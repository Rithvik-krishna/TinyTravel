import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("capture_checkouts")

TARGETS = [
    ("Sterlings Mac Hotel", "2026-11-20", "2026-11-21"),
    ("The Oberoi Bengaluru", "2026-11-20", "2026-11-21"),
]

async def main():
    results = []
    for hotel, cin, cout in TARGETS:
        logger.info("Executing real Booking.com checkout for %s...", hotel)
        res = await run_bookingcom_playbook(
            hotel_name=hotel,
            search_params={
                "check_in": cin,
                "check_out": cout,
                "guests": 2,
                "rooms": 1,
            },
            headless=True,
        )
        logger.info("Result for %s: reached=%s, payable=%s, seconds=%s",
                    hotel, res.get("reached_payment_page"), res.get("price_final_payable"), res.get("seconds"))
        results.append(res)

    out_file = Path("results/bookingcom_additional_checkouts.json")
    out_file.write_text(json.dumps(results, indent=2))
    print("Saved to", out_file)

if __name__ == "__main__":
    asyncio.run(main())
