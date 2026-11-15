import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import logging
from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook
from api.services.cohort_engine import compare_coordinated_runs

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_intersection")

CANDIDATES = [
    ("Radisson Blu Atria Bengaluru", "2026-11-20", "2026-11-21"),
    ("La Marvella", "2026-11-20", "2026-11-21"),
    ("Bloomrooms City Centre", "2026-11-20", "2026-11-21"),
]

async def probe_pair(hotel, cin, cout):
    req = {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "rooms": 1,
        "destination": "Bengaluru",
    }
    logger.info("Running Cleartrip for %s...", hotel)
    ct_res = await run_cleartrip_playbook(hotel, req, headless=False)
    logger.info("Cleartrip %s: payable=%s, room=%s, meal=%s, cancel=%s",
                hotel, ct_res.get("price_final_payable"), ct_res.get("room_type"), ct_res.get("meal_plan"), ct_res.get("cancellation_policy"))

    logger.info("Running Booking.com for %s...", hotel)
    bk_res = await run_bookingcom_playbook(hotel, req, headless=False)
    logger.info("Booking.com %s: payable=%s, room=%s, meal=%s, cancel=%s",
                hotel, bk_res.get("price_final_payable"), bk_res.get("room_type"), bk_res.get("meal_plan"), bk_res.get("cancellation_policy"))

    comp = compare_coordinated_runs(hotel, ct_res, bk_res)
    logger.info("Comparison result: %s", comp)
    return {
        "hotel": hotel,
        "cleartrip": ct_res,
        "bookingcom": bk_res,
        "comparison": comp
    }

async def main():
    results = []
    for h, cin, cout in CANDIDATES:
        res = await probe_pair(h, cin, cout)
        results.append(res)
        await asyncio.sleep(2)

    print("\n" + "=" * 90)
    for r in results:
        comp = r["comparison"]
        print(f"Hotel: {comp['hotel_name']}")
        print(f"  Status: {comp['status']} (Comparable: {comp['comparable']})")
        print(f"  Cleartrip:  INR {comp.get('cleartrip_payable')} | Cohort: {comp.get('cohort_cleartrip')}")
        print(f"  Booking.com: INR {comp.get('bookingcom_payable')} | Cohort: {comp.get('cohort_bookingcom')}")
        print(f"  Spread:     INR {comp.get('spread_inr')} ({comp.get('spread_pct')}%) | Cheaper: {comp.get('cheaper_platform')}")
        print(f"  Reason:     {comp.get('reason')}")
        print("-" * 90)

if __name__ == "__main__":
    asyncio.run(main())
