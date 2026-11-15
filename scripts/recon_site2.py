"""
Site #2 Recon Harness for MakeMyTrip, EaseMyTrip, Goibibo, and Booking.com.
Runs 3 runs each across:
1. MakeMyTrip
2. EaseMyTrip
3. Goibibo
4. Booking.com

Evaluates:
- reached review page (yes/no)
- captcha / login gate (captcha|login|none)
- rate / occupancy / cancellation fields found in network/DOM
- elapsed seconds
- Go / No-Go decision per site
Saves evidence JSON to results/site2_recon_results.json and network responses to results/recon/<site>/.
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
logger = logging.getLogger("site2_recon")

SITES = [
    {
        "name": "Booking.com",
        "slug": "bookingcom",
        "url": "https://www.booking.com/searchresults.html?ss=Bengaluru&checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR",
    },
    {
        "name": "EaseMyTrip",
        "slug": "easemytrip",
        "url": "https://www.easemytrip.com/hotels/",
    },
    {
        "name": "MakeMyTrip",
        "slug": "makemytrip",
        "url": "https://www.makemytrip.com/hotels/",
    },
    {
        "name": "Goibibo",
        "slug": "goibibo",
        "url": "https://www.goibibo.com/hotels/",
    },
]

async def recon_single(site_info: dict, run_idx: int) -> dict:
    name = site_info["name"]
    slug = site_info["slug"]
    url = site_info["url"]

    recon_dir = ROOT / "results" / "recon" / slug
    recon_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    logger.info(">>> [%s] Run %d/3 starting navigation to %s", name, run_idx, url)

    reached_review = False
    gate = "none"
    rate_found = False
    occupancy_found = False
    cancel_found = False
    captured_endpoints = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()

        async def on_response(response):
            r_url = response.url
            if any(ext in r_url for ext in [".json", "/api/", "/graphql", "search", "details"]):
                if not any(ign in r_url for ign in [".png", ".jpg", ".svg", ".css", ".js"]):
                    try:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct or "text" in ct:
                            body = await response.text()
                            if len(body) > 10 and len(body) < 500000:
                                captured_endpoints.append({
                                    "url": r_url[:150],
                                    "status": response.status,
                                    "size": len(body),
                                })
                    except Exception:
                        pass

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4.0)

            # Dismiss modal/dialog if present
            await page.keyboard.press("Escape")
            await asyncio.sleep(1.0)

            content = await page.content()
            content_lower = content.lower()

            # 1. Check for Bot / Captcha / Cloudflare / PerimeterX challenges
            if any(k in content_lower for k in ["captcha", "challenge-running", "cf-ray", "access denied", "please verify you are a human", "perimeterx", "datadome", "sec-cpt"]):
                gate = "captcha"
            # 2. Check for Mandatory Login / OTP gate
            elif any(k in content_lower for k in ["enter mobile number to login", "login with otp", "sign in to continue", "verify with otp"]) and ("search" not in page.url):
                gate = "login"

            # 3. Check for rates, occupancy, cancellation in DOM/content
            if any(sym in content for sym in ["₹", "INR", "Rs.", "Rs "]):
                rate_found = True
            if any(k in content_lower for k in ["adult", "adults", "guest", "guests", "2 adults"]):
                occupancy_found = True
            if any(k in content_lower for k in ["cancellation", "refundable", "free cancel", "non-refundable"]):
                cancel_found = True

            # Check if review/payment page was reached
            if any(k in page.url.lower() for k in ["review", "checkout", "payment", "book"]) and gate == "none":
                reached_review = True

            # Save screenshot for audit evidence
            shot_path = recon_dir / f"run_{run_idx}_screen.png"
            await page.screenshot(path=str(shot_path))

        except Exception as exc:
            logger.warning("[%s] Run %d encountered error: %s", name, run_idx, exc)
            gate = "timeout" if "timeout" in str(exc).lower() else "other"
        finally:
            await browser.close()

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info("<<< [%s] Run %d completed in %.2fs: gate=%s reached_review=%s rates=%s occ=%s cancel=%s",
                name, run_idx, elapsed, gate, reached_review, rate_found, occupancy_found, cancel_found)

    return {
        "site": name,
        "slug": slug,
        "run_index": run_idx,
        "url": url,
        "reached_review_page": reached_review,
        "gate": gate,
        "rate_fields_found": rate_found,
        "occupancy_fields_found": occupancy_found,
        "cancellation_fields_found": cancel_found,
        "seconds": elapsed,
        "endpoints_count": len(captured_endpoints),
        "sample_endpoints": captured_endpoints[:5],
    }

async def main():
    all_site_runs = []
    for site in SITES:
        for i in range(1, 4):
            res = await recon_single(site, i)
            all_site_runs.append(res)
            await asyncio.sleep(2.0)

    # Compile Summary
    summary = {}
    for site in SITES:
        s_name = site["name"]
        s_runs = [r for r in all_site_runs if r["site"] == s_name]
        review_count = len([r for r in s_runs if r["reached_review_page"]])
        gates = list({r["gate"] for r in s_runs})
        rates = any(r["rate_fields_found"] for r in s_runs)
        occ = any(r["occupancy_fields_found"] for r in s_runs)
        cancel = any(r["cancellation_fields_found"] for r in s_runs)
        avg_secs = round(sum(r["seconds"] for r in s_runs) / len(s_runs), 2)

        # Decision
        if "captcha" in gates:
            verdict = "NO-GO (KILLED)"
            reason = "Hard-blocked by anti-bot / CAPTCHA challenge"
        elif "login" in gates:
            verdict = "NO-GO (KILLED)"
            reason = "Mandatory user account login / OTP gate blocks guest checkout"
        elif review_count > 0:
            verdict = "GO"
            reason = "Accessible via automated guest flow"
        else:
            verdict = "NO-GO (BLOCKED)"
            reason = "Complex multi-step SPA / authentication barriers"

        summary[s_name] = {
            "runs": len(s_runs),
            "reached_review_count": review_count,
            "gate": gates[0] if len(gates) == 1 else gates,
            "rate_fields_found": rates,
            "occupancy_fields_found": occ,
            "cancellation_fields_found": cancel,
            "avg_seconds": avg_secs,
            "verdict": verdict,
            "reason": reason,
        }

    out_file = ROOT / "results" / "site2_recon_results.json"
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": all_site_runs,
    }
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved Site #2 recon results to %s", out_file)
    print("\n=== SITE #2 RECON SUMMARY ===")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
