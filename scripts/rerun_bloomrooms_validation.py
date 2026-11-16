import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rerun_bloomrooms")
IST = timezone(timedelta(hours=5, minutes=30))

async def main():
    hotel_name = "bloomrooms city centre"
    dates = [
        ("2026-11-20", "2026-11-21"),
        ("2026-11-27", "2026-11-28"),
    ]
    results = []

    for cin, cout in dates:
        for run_idx in [1, 2]:
            logger.info(">>> Running Cleartrip: %s | Dates: %s to %s | Run: %d", hotel_name, cin, cout, run_idx)
            params = {
                "check_in": cin,
                "check_out": cout,
                "guests": 2,
                "rooms": 1,
            }
            try:
                ct_res = await run_cleartrip_playbook(hotel_name, params, headless=False)
                # Verify total is parsed from page text
                if not ct_res.get("price_final_payable") or not ct_res.get("reached_payment_page"):
                    status = "unverified"
                else:
                    status = "verified"
                
                results.append({
                    "site": "Cleartrip",
                    "hotel_name": hotel_name,
                    "check_in": cin,
                    "check_out": cout,
                    "run_index": run_idx,
                    "status": status,
                    "reached_payment_page": ct_res.get("reached_payment_page", False),
                    "price_final_payable": ct_res.get("price_final_payable"),
                    "room_type": ct_res.get("room_type"),
                    "meal_plan": ct_res.get("meal_plan"),
                    "cancellation_policy": ct_res.get("cancellation_policy"),
                    "fee_lines": ct_res.get("fee_lines", []),
                    "payment_page_text": ct_res.get("payment_page_text", ""),
                    "seconds": ct_res.get("seconds"),
                    "notes": ct_res.get("notes"),
                })
            except Exception as e:
                logger.error("Cleartrip run failed: %s", e)
                results.append({
                    "site": "Cleartrip",
                    "hotel_name": hotel_name,
                    "check_in": cin,
                    "check_out": cout,
                    "run_index": run_idx,
                    "status": "unverified",
                    "reached_payment_page": False,
                    "price_final_payable": None,
                    "fee_lines": [],
                    "payment_page_text": "",
                    "notes": str(e),
                })

            await asyncio.sleep(2.0)

            logger.info(">>> Running Booking.com: %s | Dates: %s to %s | Run: %d", hotel_name, cin, cout, run_idx)
            try:
                bk_res = await run_bookingcom_playbook(hotel_name, params, headless=False)
                if not bk_res.get("price_final_payable") or not bk_res.get("reached_payment_page"):
                    status = "unverified"
                else:
                    status = "verified"

                results.append({
                    "site": "Booking.com",
                    "hotel_name": hotel_name,
                    "check_in": cin,
                    "check_out": cout,
                    "run_index": run_idx,
                    "status": status,
                    "reached_payment_page": bk_res.get("reached_payment_page", False),
                    "price_final_payable": bk_res.get("price_final_payable"),
                    "room_type": bk_res.get("room_type"),
                    "meal_plan": bk_res.get("meal_plan"),
                    "cancellation_policy": bk_res.get("cancellation_policy"),
                    "fee_lines": bk_res.get("fee_lines", []),
                    "payment_page_text": bk_res.get("payment_page_text", ""),
                    "seconds": bk_res.get("seconds"),
                    "notes": bk_res.get("notes"),
                })
            except Exception as e:
                logger.error("Booking.com run failed: %s", e)
                results.append({
                    "site": "Booking.com",
                    "hotel_name": hotel_name,
                    "check_in": cin,
                    "check_out": cout,
                    "run_index": run_idx,
                    "status": "unverified",
                    "reached_payment_page": False,
                    "price_final_payable": None,
                    "fee_lines": [],
                    "payment_page_text": "",
                    "notes": str(e),
                })

            await asyncio.sleep(2.0)

    out_file = Path("results/bloomrooms_current_rerun.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Saved %d rerun results to %s", len(results), out_file)

if __name__ == "__main__":
    asyncio.run(main())
