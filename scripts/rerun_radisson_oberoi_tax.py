import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rerun_rad_oberoi")

async def main():
    hotels = [
        ("Radisson Blu Atria Bengaluru", "radisson blu atria bengaluru"),
        ("The Oberoi Bengaluru", "the oberoi bengaluru"),
    ]
    cin = "2026-11-20"
    cout = "2026-11-21"

    results = []
    for disp, key in hotels:
        search_params = {
            "check_in": cin,
            "check_out": cout,
            "guests": 2,
            "rooms": 1,
        }
        res = await run_bookingcom_playbook(key, search_params, headless=False)
        res["hotel_display_name"] = disp
        results.append(res)
        logger.info("Result for %s: reached_payment=%s, payable=%s, fee_lines=%s, screenshot=%s",
                    disp, res.get("reached_payment_page"), res.get("price_final_payable"),
                    res.get("fee_lines"), res.get("screenshot_path"))
        await asyncio.sleep(2.0)

    Path("results/booking_tax_rad_oberoi.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
