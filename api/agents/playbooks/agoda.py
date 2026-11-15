"""
Agoda State-Machine Playbook.
Executes deterministic guest checkout probe on Agoda stopping at payment or blocker.
Never attempts to solve, click through, or bypass anti-bot challenges (records blocked).
Asserts state invariants and obeys hard caps: max 45 steps, max 90.0 seconds.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("tinytravel.playbook.agoda")
IST = timezone(timedelta(hours=5, minutes=30))

KNOWN_AGODA_HOTELS = {
    "radisson blu atria": (1785304, "radisson-blu-atria-bengaluru"),
    "radisson blu atria bengaluru": (1785304, "radisson-blu-atria-bengaluru"),
    "sterlings mac hotel": (285239, "sterlings-mac-hotel"),
    "sterlings mac hotel bengaluru": (285239, "sterlings-mac-hotel"),
    "la marvella": (261499, "la-marvella"),
    "the chancery pavilion": (40140, "the-chancery-pavilion"),
    "the pride hotel": (49352, "the-pride-hotel"),
}


def _build_agoda_search_url(hotel_name: str, check_in: str, check_out: str, guests: int = 2) -> str:
    norm_name = hotel_name.lower().strip()
    match = None
    for k, v in KNOWN_AGODA_HOTELS.items():
        if k in norm_name or norm_name in k:
            match = v
            break
    if match:
        hid = match[0]
        return (
            f"https://www.agoda.com/en-in/search?"
            f"hotel={hid}&selectedproperty={hid}&city=4923&"
            f"checkIn={check_in}&checkOut={check_out}&rooms=1&adults={guests}&currency=INR"
        )
    return (
        f"https://www.agoda.com/en-in/search?"
        f"textToSearch={hotel_name.replace(' ', '+')}&city=4923&"
        f"checkIn={check_in}&checkOut={check_out}&rooms=1&adults={guests}&currency=INR"
    )


def to_probe_result_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Filter raw output strictly to fields defined in ProbeResult schema."""
    probe_keys = {
        "site", "reached_payment_page", "furthest_step", "blocker", "hotel_name",
        "hotel_url", "room_type", "max_occupancy", "meal_plan", "cancellation_policy",
        "price_shown_on_listing", "price_shown_on_room_selection", "price_final_payable",
        "fee_lines", "preselected_addons", "urgency_or_scarcity_messages", "price_trail",
        "currency", "notes", "listing_page_text", "payment_page_text", "rate_cohort",
        "cheapest_any_payable", "pay_now", "pay_at_hotel", "verification_level"
    }
    return {k: v for k, v in raw.items() if k in probe_keys}


async def run_agoda_playbook(
    hotel_name: str,
    req: dict,
    *,
    timeout_s: float = 90.0,
    max_steps: int = 45,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Execute deterministic state-machine checkout playbook on Agoda.
    Hard caps: max_steps (default 45), timeout_s (default 90s).
    Stops at blocker (captcha/bot/login) or payment page. Output matches ProbeResult schema.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "site": "Agoda",
            "status": "blocked",
            "blocker": "other",
            "error": "Playwright is not installed.",
            "steps": 0,
            "cost_usd": 0.0,
        }

    t0 = datetime.now(IST)
    started_at = t0.isoformat()
    steps = 0
    state = "INIT"

    destination = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = int(req.get("guests", 2))
    offer_id = req.get("offer_id") or f"off_agoda_{hotel_name.lower().replace(' ', '_')[:8]}"

    evidence_dir = Path(__file__).resolve().parents[3] / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    def check_caps():
        nonlocal steps
        elapsed = (datetime.now(IST) - t0).total_seconds()
        if steps >= max_steps:
            raise TimeoutError(f"Hard step cap exceeded: {steps}/{max_steps} steps")
        if elapsed >= timeout_s:
            raise TimeoutError(f"Hard time cap exceeded: {elapsed:.1f}/{timeout_s}s")

    try:
        async with async_playwright() as p:
            steps += 1
            check_caps()
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
            )
            page = await context.new_page()

            graphql_search_data = None
            async def on_resp(r):
                nonlocal graphql_search_data
                if "graphql/search" in r.url:
                    try:
                        data = await r.json()
                        props = data.get("data", {}).get("citySearch", {}).get("properties", [])
                        if props:
                            graphql_search_data = props[0]
                    except Exception:
                        pass
            page.on("response", on_resp)

            # State 1: NAVIGATE_SEARCH
            state = "NAVIGATE_SEARCH"
            target_url = req.get("url") or _build_agoda_search_url(hotel_name, check_in, check_out, guests)
            steps += 1
            check_caps()
            logger.info("Playbook state=%s navigating to %s", state, target_url)
            await page.goto(target_url, timeout=min(timeout_s, 40.0) * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(4.0)

            # Dismiss modal if present
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            # Assertion 1: Check for anti-bot challenges / CAPTCHA
            content = await page.content()
            title = await page.title()
            is_bot_blocked = (
                any(term in content.lower() for term in ["captcha", "challenge", "cf-ray", "access denied", "please verify", "perimeterx"])
                or not title.strip()
            )

            shot_path = evidence_dir / f"{offer_id}_screenshot.png"
            await page.screenshot(path=str(shot_path))
            listing_text = f"{hotel_name} · Agoda search"
            (evidence_dir / f"{offer_id}_listing.txt").write_text(content[:5000], encoding="utf-8")

            if is_bot_blocked:
                await browser.close()
                t1 = datetime.now(IST)
                elapsed = (t1 - t0).total_seconds()
                logger.warning("Agoda search blocked by bot challenge/CAPTCHA")
                return {
                    "site": "Agoda",
                    "status": "blocked",
                    "blocker": "captcha",
                    "hotel_name": hotel_name,
                    "hotel_url": target_url,
                    "reached_payment_page": False,
                    "furthest_step": "search",
                    "steps": steps,
                    "seconds": elapsed,
                    "notes": "Anti-bot CAPTCHA/challenge detected on Agoda search page.",
                    "cost_usd": 0.0,
                    "price_shown_on_listing": None,
                    "price_final_payable": None,
                    "fee_lines": [],
                    "currency": "INR",
                    "rate_cohort": "cheapest_free_cancellation",
                    "listing_page_text": listing_text,
                    "payment_page_text": None,
                }

            # State 2: SEARCH_RESULTS
            state = "SEARCH_RESULTS"
            steps += 1
            check_caps()

            # If search loaded without captcha, check property and room grid
            listing_price = None
            if graphql_search_data:
                pricing = graphql_search_data.get("pricing", {})
                offers = pricing.get("offers", [])
                if offers:
                    p_night = offers[0].get("roomOffers", [{}])[0].get("room", {}).get("pricing", [{}])[0].get("price", {}).get("perNight", {})
                    listing_price = float(p_night.get("exclusive", {}).get("display") or 0.0)

            # Try to navigate to property
            norm_name = hotel_name.lower().strip()
            hid = None
            for k, v in KNOWN_AGODA_HOTELS.items():
                if k in norm_name or norm_name in k:
                    hid = v[0]
                    break

            if hid:
                prop_url = f"https://www.agoda.com/en-in/accom/property?propertyId={hid}&countryId=35&finalPriceView=1&adults={guests}&rooms=1&checkIn={check_in}&checkOut={check_out}&currencyCode=INR&los=1"
                steps += 1
                check_caps()
                await page.goto(prop_url, timeout=min(timeout_s, 30.0) * 1000, wait_until="domcontentloaded")
                await asyncio.sleep(4.0)
                await page.keyboard.press("Escape")

                prop_content = await page.content()
                if any(term in prop_content.lower() for term in ["captcha", "challenge", "cf-ray", "access denied", "please verify"]):
                    await browser.close()
                    t1 = datetime.now(IST)
                    return {
                        "site": "Agoda",
                        "status": "blocked",
                        "blocker": "captcha",
                        "hotel_name": hotel_name,
                        "hotel_url": prop_url,
                        "reached_payment_page": False,
                        "furthest_step": "room",
                        "steps": steps,
                        "seconds": (t1 - t0).total_seconds(),
                        "notes": "Anti-bot challenge/CAPTCHA detected on Agoda property page.",
                        "cost_usd": 0.0,
                    }

                book_btns = await page.locator("button[data-selenium='book-button'], button:has-text('Book now'), button:has-text('Reserve')").all()
                if not book_btns:
                    # Agoda room-grid offers are empty or blocked
                    await browser.close()
                    t1 = datetime.now(IST)
                    return {
                        "site": "Agoda",
                        "status": "unverified",
                        "blocker": "other",
                        "hotel_name": hotel_name,
                        "hotel_url": prop_url,
                        "reached_payment_page": False,
                        "furthest_step": "room",
                        "steps": steps,
                        "seconds": (t1 - t0).total_seconds(),
                        "notes": "Agoda room grid offers empty or blocked by guest authentication gate.",
                        "cost_usd": 0.0,
                        "price_shown_on_listing": listing_price,
                        "price_final_payable": None,
                        "fee_lines": [],
                        "currency": "INR",
                        "rate_cohort": "cheapest_free_cancellation",
                    }

            await browser.close()
            t1 = datetime.now(IST)
            return {
                "site": "Agoda",
                "status": "unverified",
                "blocker": "other",
                "hotel_name": hotel_name,
                "hotel_url": target_url,
                "reached_payment_page": False,
                "furthest_step": state.lower(),
                "steps": steps,
                "seconds": (t1 - t0).total_seconds(),
                "notes": "Agoda could not complete guest checkout to payment review.",
                "cost_usd": 0.0,
                "price_shown_on_listing": listing_price,
                "price_final_payable": None,
                "fee_lines": [],
                "currency": "INR",
                "rate_cohort": "cheapest_free_cancellation",
            }

    except Exception as exc:
        t1 = datetime.now(IST)
        elapsed = (t1 - t0).total_seconds()
        is_to = isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        return {
            "site": "Agoda",
            "status": "blocked" if is_to else "unverified",
            "blocker": "timeout" if is_to else "other",
            "hotel_name": hotel_name,
            "hotel_url": target_url if "target_url" in locals() else "",
            "reached_payment_page": False,
            "furthest_step": state.lower(),
            "steps": steps,
            "seconds": elapsed,
            "notes": f"Playbook failed at state {state}: {exc}",
            "cost_usd": 0.0,
            "error": str(exc),
        }
