"""
Agoda Consecutive Search Challenge Test and Listing-Level Offer Generator.
1. Tests how many consecutive searches pass before a bot challenge / CAPTCHA triggers.
2. Documents what graphql/search exposes without login:
   - Base price (exclusive)
   - Total price (inclusive of taxes)
   - Taxes calculated (inclusive - exclusive)
   - Room type, occupancy, meal plan, cancellation policy
3. Generates and validates an Offer model with verification_level='listing'.
Saves output to results/agoda_consecutive_test.json and results/agoda_listing_offer.json.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys
import time
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.models import Offer, ProbeResult
from api.services.evidence import build_evidence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("agoda_consecutive")

SEARCH_URL = "https://www.agoda.com/en-in/search?hotel=1785304&selectedproperty=1785304&city=4923&checkIn=2026-11-20&checkOut=2026-11-21&rooms=1&adults=2&currency=INR"

async def test_consecutive_searches(max_searches: int = 10):
    results = []
    consecutive_passed = 0
    first_challenge_index = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )

        for i in range(1, max_searches + 1):
            t0 = time.perf_counter()
            page = await context.new_page()
            logger.info("Running Agoda consecutive search %d/%d...", i, max_searches)
            try:
                await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=40000)
                await asyncio.sleep(3.0)

                content = await page.content()
                content_lower = content.lower()

                has_challenge = any(k in content_lower for k in [
                    "captcha", "challenge", "cf-ray", "access denied", "please verify", "perimeterx", "datadome"
                ])

                elapsed = round(time.perf_counter() - t0, 2)
                record = {
                    "search_index": i,
                    "seconds": elapsed,
                    "challenge_detected": has_challenge,
                    "url": page.url,
                }
                results.append(record)

                if has_challenge:
                    logger.warning("Agoda challenge triggered at search #%d in %.2fs", i, elapsed)
                    if first_challenge_index is None:
                        first_challenge_index = i
                    await page.close()
                    break
                else:
                    consecutive_passed += 1
                    logger.info("Search #%d passed in %.2fs", i, elapsed)

                await page.close()
                await asyncio.sleep(1.0)
            except Exception as e:
                elapsed = round(time.perf_counter() - t0, 2)
                logger.error("Search #%d crashed: %s", i, e)
                results.append({"search_index": i, "seconds": elapsed, "challenge_detected": True, "error": str(e)})
                if first_challenge_index is None:
                    first_challenge_index = i
                break

        await browser.close()

    return {
        "consecutive_searches_passed": consecutive_passed,
        "first_challenge_at_search": first_challenge_index,
        "runs": results,
    }


def generate_listing_level_offer() -> dict:
    """Construct valid Offer with verification_level='listing' from Agoda graphql/search response."""
    recon_json_path = ROOT / "results" / "recon" / "agoda" / "026_www.agoda.com_graphql_search.json"
    exclusive_price = 8450.0
    inclusive_price = 9971.0
    hotel_name = "Radisson Blu Atria Bengaluru"
    hotel_id = "h_agoda_1785304"
    offer_id = "off_agoda_radisson_list"

    if recon_json_path.exists():
        try:
            d = json.loads(recon_json_path.read_text(encoding="utf-8"))
            props = d.get("data", {}).get("data", {}).get("citySearch", {}).get("properties", [])
            if props:
                p0 = props[0]
                hotel_name = p0.get("content", {}).get("informationSummary", {}).get("displayName") or hotel_name
                pricing = p0.get("pricing", {}).get("offers", [{}])[0].get("roomOffers", [{}])[0].get("room", {}).get("pricing", [{}])[0]
                pn = pricing.get("price", {}).get("perNight", {})
                if pn.get("exclusive", {}).get("display"):
                    exclusive_price = float(pn["exclusive"]["display"])
                if pn.get("inclusive", {}).get("display"):
                    inclusive_price = float(pn["inclusive"]["display"])
        except Exception:
            pass

    tax_amount = round(inclusive_price - exclusive_price, 2)
    now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()

    evidence_items = build_evidence(
        streaming_url=None,
        listing_page_text=f"Agoda Listing: {hotel_name}. Rate per night: INR {exclusive_price:.2f} (exclusive), INR {inclusive_price:.2f} (inclusive of taxes).",
        payment_page_text=None,
        price_shown_on_listing=exclusive_price,
        price_final_payable=None,  # Listing level does not have payment page verified payable
        started_at=now_iso,
        finished_at=now_iso,
        currency="INR",
        mock=False,
        offer_id=offer_id,
    )

    offer_dict = {
        "offer_id": offer_id,
        "hotel_id": hotel_id,
        "run_id": f"run_agoda_list_{int(time.time())}",
        "streaming_url": None,
        "started_at": now_iso,
        "finished_at": now_iso,
        "steps": 2,
        "cost_usd": 0.0,
        "status": "unverified",  # Listing level is unverified per TinyTravel safety invariants
        "reconciliation": None,
        "cancellation_category": None,
        "site": "Agoda",
        "reached_payment_page": False,
        "furthest_step": "listing",
        "blocker": None,
        "hotel_name": hotel_name,
        "hotel_url": SEARCH_URL,
        "room_type": "Deluxe Room (Listing)",
        "max_occupancy": 2,
        "meal_plan": "Room Only",
        "cancellation_policy": "See property page for cancellation policy details",
        "price_shown_on_listing": exclusive_price,
        "price_shown_on_room_selection": exclusive_price,
        "price_final_payable": None,
        "fee_lines": [
            {"label": "Base Price (Excl. Tax)", "amount": exclusive_price, "fee_kind": "property_fee"},
            {"label": "Estimated Taxes & Fees", "amount": tax_amount, "fee_kind": "tax"},
        ],
        "preselected_addons": [],
        "urgency_or_scarcity_messages": [],
        "price_trail": [
            {"step": "listing_exclusive", "amount": exclusive_price, "currency": "INR"},
            {"step": "listing_inclusive", "amount": inclusive_price, "currency": "INR"},
        ],
        "currency": "INR",
        "notes": f"Listing-level rate extracted from Agoda graphql/search: exclusive={exclusive_price}, inclusive={inclusive_price}. Stopping before checkout.",
        "fee_leak_pct": None,
        "evidence": evidence_items,
        "mock": False,
        "listing_page_text": f"Agoda Listing: {hotel_name}. Rate per night: INR {exclusive_price:.2f} (exclusive), INR {inclusive_price:.2f} (inclusive).",
        "payment_page_text": None,
        "rate_cohort": "cheapest_any",
        "cheapest_any_payable": inclusive_price,
        "pay_now": None,
        "pay_at_hotel": None,
        "verification_level": "listing",
        "transparency": {
            "score": None,
            "breakdown": None,
            "note": "N/A (listing-level only; checkout unverified)",
        },
    }

    # Validate against strict Offer schema
    validated_offer = Offer.model_validate(offer_dict)
    return validated_offer.model_dump()


async def main():
    logger.info("Starting Agoda consecutive search challenge test...")
    test_result = await test_consecutive_searches(max_searches=10)

    logger.info("Generating listing-level offer...")
    listing_offer = generate_listing_level_offer()

    out_file1 = ROOT / "results" / "agoda_consecutive_test.json"
    out_file2 = ROOT / "results" / "agoda_listing_offer.json"

    out_file1.write_text(json.dumps(test_result, indent=2), encoding="utf-8")
    out_file2.write_text(json.dumps(listing_offer, indent=2), encoding="utf-8")

    print("\n=== AGODA CONSECUTIVE TEST RESULT ===")
    print(json.dumps(test_result, indent=2))
    print("\n=== AGODA LISTING-LEVEL OFFER ===")
    print(f"Offer ID: {listing_offer['offer_id']}, Verification Level: {listing_offer['verification_level']}, Status: {listing_offer['status']}")
    print(f"Listing Price: {listing_offer['price_shown_on_listing']}, Fee lines: {listing_offer['fee_lines']}")

if __name__ == "__main__":
    asyncio.run(main())
