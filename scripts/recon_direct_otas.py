"""
Reconnaissance script for Global OTAs and Domestic OTAs.
Evaluates:
- Expedia, Hotels.com, Trip.com, Priceline
- Yatra, ixigo, redBus, OneFineRate
3 runs each across 2 stay dates: 2026-11-20 to 2026-11-21 and 2026-12-05 to 2026-12-06.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import sys
import time
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recon_otas")

DATES = [
    {"cin": "2026-11-20", "cout": "2026-11-21", "cin_slash": "20/11/2026", "cout_slash": "21/11/2026", "cin_compact": "20261120", "cout_compact": "20261121"},
    {"cin": "2026-12-05", "cout": "2026-12-06", "cin_slash": "05/12/2026", "cout_slash": "06/12/2026", "cin_compact": "20261205", "cout_compact": "20261206"},
    {"cin": "2026-11-20", "cout": "2026-11-21", "cin_slash": "20/11/2026", "cout_slash": "21/11/2026", "cin_compact": "20261120", "cout_compact": "20261121"},
]

PLATFORMS = [
    {
        "category": "Global OTA",
        "name": "Expedia",
        "slug": "expedia",
        "get_url": lambda d: f"https://www.expedia.co.in/Hotel-Search?destination=Bengaluru&startDate={d['cin']}&endDate={d['cout']}&adults=2",
    },
    {
        "category": "Global OTA",
        "name": "Hotels.com",
        "slug": "hotelscom",
        "get_url": lambda d: f"https://in.hotels.com/Hotel-Search?destination=Bengaluru&startDate={d['cin']}&endDate={d['cout']}&adults=2",
    },
    {
        "category": "Global OTA",
        "name": "Trip.com",
        "slug": "tripcom",
        "get_url": lambda d: f"https://in.trip.com/hotels/list?city=1028&checkIn={d['cin']}&checkOut={d['cout']}&crn=1&adult=2",
    },
    {
        "category": "Global OTA",
        "name": "Priceline",
        "slug": "priceline",
        "get_url": lambda d: f"https://www.priceline.com/relax/in/bengaluru/hotels?check-in={d['cin_compact']}&check-out={d['cout_compact']}&rooms=1&adults=2",
    },
    {
        "category": "Domestic OTA",
        "name": "Yatra",
        "slug": "yatra",
        "get_url": lambda d: f"https://hotel.yatra.com/hotel-search/dom/search?city.name=Bangalore&checkInDate={d['cin_slash'].replace('/', '%2F')}&checkOutDate={d['cout_slash'].replace('/', '%2F')}&roomReq[0].NoOfAdults=2",
    },
    {
        "category": "Domestic OTA",
        "name": "ixigo",
        "slug": "ixigo",
        "get_url": lambda d: f"https://www.ixigo.com/hotels/search?destination=Bengaluru&checkin={d['cin']}&checkout={d['cout']}&rooms=1&adults=2",
    },
    {
        "category": "Domestic OTA",
        "name": "redBus",
        "slug": "redbus",
        "get_url": lambda d: f"https://www.redbus.in/hotels/search?destination=Bangalore&checkin={d['cin']}&checkout={d['cout']}&adults=2",
    },
    {
        "category": "Domestic OTA",
        "name": "OneFineRate",
        "slug": "onefinerate",
        "get_url": lambda d: "https://www.onefinerate.com",
    },
]


def detect_bot_gate(html: str, status_code: int = 200) -> str:
    lower = html.lower()
    if status_code in (403, 429):
        return "captcha"
    if any(c in lower for c in ["cloudflare", "cf-chl", "just a moment...", "turnstile"]):
        return "captcha"
    if any(c in lower for c in ["perimeterx", "px-captcha", "press & hold", "access denied"]):
        return "captcha"
    if any(c in lower for c in ["akamai", "geetest", "datadome", "recaptcha", "hcaptcha"]):
        return "captcha"
    if any(c in lower for c in ["login to continue", "sign in to book", "please enter your otp"]):
        return "login"
    return "none"


async def recon_platform(platform: dict) -> list[dict]:
    name = platform["name"]
    slug = platform["slug"]
    category = platform["category"]

    results_dir = ROOT / "results" / "recon" / slug
    results_dir.mkdir(parents=True, exist_ok=True)

    runs = []

    for run_idx in range(1, 4):
        d = DATES[run_idx - 1]
        url = platform["get_url"](d)
        logger.info(">>> [%s] Run %d/3 -> %s (dates: %s to %s)", name, run_idx, url, d["cin"], d["cout"])

        t0 = time.perf_counter()
        gate = "none"
        reached_review = False
        rate_found = False
        occupancy_found = False
        cancel_found = False
        meal_found = False
        fee_lines_reconcile = None
        price_val = None
        captured_endpoints = []
        status_code = 200
        page_title = ""

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    locale="en-IN",
                    timezone_id="Asia/Kolkata",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

                async def on_response(response):
                    r_url = response.url
                    if any(x in r_url for x in [".json", "/api/", "/graphql", "search", "hotel", "rate", "price"]):
                        if not any(ign in r_url for ign in [".png", ".jpg", ".svg", ".css", ".js", "analytics", "telemetry"]):
                            captured_endpoints.append({
                                "url": r_url[:120],
                                "status": response.status,
                            })

                page.on("response", on_response)

                try:
                    resp = await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    if resp:
                        status_code = resp.status
                except Exception as e:
                    logger.warning("[%s] Goto error: %s", name, e)
                    if "net::ERR_" in str(e):
                        gate = "other"

                await asyncio.sleep(4.0)

                html = await page.content()
                page_title = await page.title()
                scr_path = results_dir / f"run_{run_idx}_screen.png"
                await page.screenshot(path=str(scr_path))

                # Check gate
                if gate == "none":
                    gate = detect_bot_gate(html, status_code)

                # Search content
                lower_html = html.lower()
                rate_found = any(sym in html for sym in ["₹", "INR", "Rs.", "price"]) and bool(re.search(r"[₹\d,]{3,}", html))
                occupancy_found = any(term in lower_html for term in ["adult", "guest", "room", "occupan"])
                cancel_found = any(term in lower_html for term in ["cancellation", "refundable", "free cancel"])
                meal_found = any(term in lower_html for term in ["breakfast", "meal", "room only", "dinner"])

                # Check if review/payment reached
                reached_review = any(term in lower_html for term in ["review your booking", "traveller details", "payment options", "proceed to pay", "price breakdown"]) and not (gate in ["captcha", "login"])

                # Parse price sample
                prices = re.findall(r"₹\s*([0-9,]+)", html)
                if prices:
                    cleaned_prices = [float(p.replace(",", "")) for p in prices if len(p.replace(",", "")) >= 3]
                    if cleaned_prices:
                        price_val = min(cleaned_prices)

                await browser.close()
        except Exception as e:
            logger.error("[%s] Run %d failed with error: %s", name, run_idx, e)
            gate = "other"

        elapsed = round(time.perf_counter() - t0, 2)
        runs.append({
            "run_index": run_idx,
            "stay_dates": f"{d['cin']} to {d['cout']}",
            "elapsed_seconds": elapsed,
            "status_code": status_code,
            "page_title": page_title[:80],
            "reached_review_page": reached_review,
            "gate": gate,
            "fields_found": {
                "rate": rate_found,
                "occupancy": occupancy_found,
                "cancellation": cancel_found,
                "meal": meal_found,
            },
            "sample_price": price_val,
            "endpoints_captured_count": len(captured_endpoints),
            "endpoints_sample": captured_endpoints[:5],
            "screenshot": f"results/recon/{slug}/run_{run_idx}_screen.png",
        })

    return runs


async def main():
    all_results = {}
    for p in PLATFORMS:
        runs = await recon_platform(p)
        all_results[p["slug"]] = {
            "name": p["name"],
            "category": p["category"],
            "slug": p["slug"],
            "runs": runs,
        }
        # Save incremental progress
        with open(ROOT / "results" / "recon_direct_otas.json", "w") as f:
            json.dump(all_results, f, indent=2)

    logger.info("Direct OTA reconnaissance completed. Saved to results/recon_direct_otas.json")


if __name__ == "__main__":
    asyncio.run(main())
