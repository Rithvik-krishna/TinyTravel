import asyncio
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rerun_rad_tax")

async def main():
    cin = "2026-11-20"
    cout = "2026-11-21"
    search_params = {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "rooms": 1,
    }
    res = await run_bookingcom_playbook("radisson blu atria bengaluru", search_params, headless=False)
    logger.info("Result for Radisson Blu Atria: reached_payment=%s, payable=%s, fee_lines=%s, screenshot=%s",
                res.get("reached_payment_page"), res.get("price_final_payable"),
                res.get("fee_lines"), res.get("screenshot_path"))
    Path("results/booking_tax_radisson_only.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
