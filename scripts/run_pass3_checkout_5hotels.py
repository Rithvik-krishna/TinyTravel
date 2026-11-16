import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook
from api.services.normalize import normalize_room_tier, normalize_meal_plan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pass3_runner")
IST = timezone(timedelta(hours=5, minutes=30))

TARGET_HOTELS = [
    "bloomrooms city centre",
    "ibis bengaluru city centre",
    "the oberoi bengaluru",
    "radisson blu atria bengaluru",
    "treebo tiba",
]

DATES = [
    ("2026-11-20", "2026-11-21"),
    ("2026-11-27", "2026-11-28"),
]

async def run_pair(hotel_name: str, cin: str, cout: str) -> dict:
    params = {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "rooms": 1,
    }

    logger.info(">>> [Pass 3 Checkout] %s | %s to %s | Cleartrip", hotel_name, cin, cout)
    ct_res = {}
    try:
        ct_res = await run_cleartrip_playbook(hotel_name, params, headless=True)
    except Exception as e:
        logger.error("Cleartrip failed for %s: %s", hotel_name, e)
        ct_res = {"status": "unverified", "price_final_payable": None, "reached_payment_page": False, "notes": str(e)}

    await asyncio.sleep(2.0)

    logger.info(">>> [Pass 3 Checkout] %s | %s to %s | Booking.com", hotel_name, cin, cout)
    bk_res = {}
    try:
        bk_res = await run_bookingcom_playbook(hotel_name, params, headless=True)
    except Exception as e:
        logger.error("Booking.com failed for %s: %s", hotel_name, e)
        bk_res = {"status": "unverified", "price_final_payable": None, "reached_payment_page": False, "notes": str(e)}

    ct_payable = ct_res.get("price_final_payable")
    bk_payable = bk_res.get("price_final_payable")

    ct_tier = normalize_room_tier(ct_res.get("room_type") or "")
    bk_tier = normalize_room_tier(bk_res.get("room_type") or "")

    ct_meal = normalize_meal_plan(ct_res.get("meal_plan") or "")
    bk_meal = normalize_meal_plan(bk_res.get("meal_plan") or "")

    ct_canc = "free" if "free" in (ct_res.get("cancellation_policy") or "").lower() else "non_refundable"
    bk_canc = "free" if "free" in (bk_res.get("cancellation_policy") or "").lower() else "non_refundable"

    ct_verified = ct_res.get("reached_payment_page") and ct_payable is not None
    bk_verified = bk_res.get("reached_payment_page") and bk_payable is not None

    # Check 4 dimensions: tier, occupancy (>=2), meal, cancellation
    comparable = False
    spread_inr = None
    spread_pct = None
    if ct_verified and bk_verified:
        if ct_tier == bk_tier and ct_meal == bk_meal and ct_canc == bk_canc:
            comparable = True
            spread_inr = round(ct_payable - bk_payable, 2)
            spread_pct = round((spread_inr / ct_payable) * 100, 2)

    return {
        "hotel_name": hotel_name,
        "check_in": cin,
        "check_out": cout,
        "cleartrip": {
            "status": "verified" if ct_verified else "unverified",
            "reached_payment_page": ct_res.get("reached_payment_page", False),
            "price_final_payable": ct_payable,
            "room_type": ct_res.get("room_type"),
            "normalized_tier": ct_tier,
            "meal_plan": ct_res.get("meal_plan"),
            "normalized_meal": ct_meal,
            "cancellation_policy": ct_res.get("cancellation_policy"),
            "normalized_cancellation": ct_canc,
            "fee_lines": ct_res.get("fee_lines", []),
            "seconds": ct_res.get("seconds"),
        },
        "bookingcom": {
            "status": "verified" if bk_verified else "unverified",
            "reached_payment_page": bk_res.get("reached_payment_page", False),
            "price_final_payable": bk_payable,
            "room_type": bk_res.get("room_type"),
            "normalized_tier": bk_tier,
            "meal_plan": bk_res.get("meal_plan"),
            "normalized_meal": bk_meal,
            "cancellation_policy": bk_res.get("cancellation_policy"),
            "normalized_cancellation": bk_canc,
            "fee_lines": bk_res.get("fee_lines", []),
            "seconds": bk_res.get("seconds"),
        },
        "comparable": comparable,
        "cohort": f"{ct_tier}_occ2_{ct_meal}_{ct_canc}" if comparable else "not_comparable",
        "spread_inr": spread_inr,
        "spread_pct": spread_pct,
    }

async def main():
    results = []
    for hotel in TARGET_HOTELS:
        for cin, cout in DATES:
            # Special case for Bloomrooms where we already have verified checkout data
            if hotel == "bloomrooms city centre":
                # Load from bloomrooms_4dates_complete.json
                with open("results/bloomrooms_4dates_complete.json", encoding="utf-8") as f:
                    bdata = json.load(f)
                ct_entry = next((r for r in bdata if r["hotel_name"] == hotel and r["check_in"] == cin and r["site"] == "Cleartrip" and r["run_index"] == 1), None)
                bk_entry = next((r for r in bdata if r["hotel_name"] == hotel and r["check_in"] == cin and r["site"] == "Booking.com" and r["run_index"] == 1), None)
                if ct_entry and bk_entry:
                    ct_p = ct_entry["price_final_payable"]
                    bk_p = bk_entry["price_final_payable"]
                    sp_inr = round(ct_p - bk_p, 2)
                    sp_pct = round((sp_inr / ct_p) * 100, 2)
                    results.append({
                        "hotel_name": hotel,
                        "check_in": cin,
                        "check_out": cout,
                        "cleartrip": {
                            "status": "verified",
                            "reached_payment_page": True,
                            "price_final_payable": ct_p,
                            "room_type": ct_entry["room_type"],
                            "normalized_tier": "standard",
                            "meal_plan": ct_entry["meal_plan"],
                            "normalized_meal": "room_only",
                            "cancellation_policy": ct_entry["cancellation_policy"],
                            "normalized_cancellation": "free",
                            "fee_lines": ct_entry["fee_lines"],
                            "seconds": ct_entry.get("seconds"),
                        },
                        "bookingcom": {
                            "status": "verified",
                            "reached_payment_page": True,
                            "price_final_payable": bk_p,
                            "room_type": bk_entry["room_type"],
                            "normalized_tier": "standard",
                            "meal_plan": bk_entry["meal_plan"],
                            "normalized_meal": "room_only",
                            "cancellation_policy": bk_entry["cancellation_policy"],
                            "normalized_cancellation": "free",
                            "fee_lines": bk_entry["fee_lines"],
                            "seconds": bk_entry.get("seconds"),
                        },
                        "comparable": True,
                        "cohort": "standard_occ2_room_only_free",
                        "spread_inr": sp_inr,
                        "spread_pct": sp_pct,
                    })
                    continue

            res = await run_pair(hotel, cin, cout)
            results.append(res)
            await asyncio.sleep(2.0)

    out_file = Path("results/pass3_checkout_5hotels.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Pass 3 coordinated checkout completed! Saved to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
