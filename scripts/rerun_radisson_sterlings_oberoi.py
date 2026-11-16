import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rerun_radisson_sterlings_oberoi")
IST = timezone(timedelta(hours=5, minutes=30))

async def main():
    hotels = [
        "radisson blu atria bengaluru",
        "sterlings mac hotel",
        "the oberoi bengaluru",
    ]
    cin = "2026-11-20"
    cout = "2026-11-21"
    results = []

    for hotel_name in hotels:
        logger.info(">>> Running Booking.com checkout for %s (%s to %s)...", hotel_name, cin, cout)
        params = {
            "check_in": cin,
            "check_out": cout,
            "guests": 2,
            "rooms": 1,
        }
        try:
            res = await run_bookingcom_playbook(hotel_name, params, headless=False)
            results.append(res)
            logger.info("Result for %s: reached=%s, payable=%s, fee_lines=%s",
                        hotel_name, res.get("reached_payment_page"), res.get("price_final_payable"), res.get("fee_lines"))
        except Exception as e:
            logger.error("Failed for %s: %s", hotel_name, e)
            results.append({
                "hotel_name": hotel_name,
                "reached_payment_page": False,
                "price_final_payable": None,
                "fee_lines": [],
                "notes": f"Error: {e}",
            })
        await asyncio.sleep(2.0)

    out_file = Path("results/bookingcom_rerun_radisson_sterlings_oberoi.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Finished running 3 hotels. Saved to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
