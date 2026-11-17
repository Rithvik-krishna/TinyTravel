import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rerun")
IST = timezone(timedelta(hours=5, minutes=30))

async def main():
    results = {}
    
    # 1. Radisson on Booking.com 2026-11-20 (fixed parser)
    logger.info("=== 1. Radisson Booking.com 2026-11-20 ===")
    bk_rad_20 = await run_bookingcom_playbook("radisson blu atria bengaluru", {
        "check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2
    }, headless=True)
    results["radisson_bk_20"] = bk_rad_20

    await asyncio.sleep(2.0)

    # 2. Radisson on Booking.com 2026-11-27 (fixed parser)
    logger.info("=== 2. Radisson Booking.com 2026-11-27 ===")
    bk_rad_27 = await run_bookingcom_playbook("radisson blu atria bengaluru", {
        "check_in": "2026-11-27", "check_out": "2026-11-28", "guests": 2
    }, headless=True)
    results["radisson_bk_27"] = bk_rad_27

    await asyncio.sleep(2.0)

    # 3. The Oberoi on Booking.com 2026-11-27
    logger.info("=== 3. The Oberoi Booking.com 2026-11-27 ===")
    bk_obe_27 = await run_bookingcom_playbook("the oberoi bengaluru", {
        "check_in": "2026-11-27", "check_out": "2026-11-28", "guests": 2
    }, headless=True)
    results["oberoi_bk_27"] = bk_obe_27

    await asyncio.sleep(2.0)

    # 4. Bloomrooms Drift Rerun (35+ min apart from 11:30 run)
    logger.info("=== 4. Bloomrooms Drift Rerun (2026-11-20) ===")
    ct_bloom_drift = await run_cleartrip_playbook("bloomrooms city centre", {
        "check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2
    }, headless=True)
    results["bloomrooms_ct_drift"] = ct_bloom_drift

    await asyncio.sleep(2.0)

    bk_bloom_drift = await run_bookingcom_playbook("bloomrooms city centre", {
        "check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2
    }, headless=True)
    results["bloomrooms_bk_drift"] = bk_bloom_drift

    await asyncio.sleep(2.0)

    # 5. Radisson Cleartrip Drift Rerun (35+ min apart from 11:31 run)
    logger.info("=== 5. Radisson Cleartrip Drift Rerun (2026-11-20) ===")
    ct_rad_drift = await run_cleartrip_playbook("radisson blu atria bengaluru", {
        "check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2
    }, headless=True)
    results["radisson_ct_drift"] = ct_rad_drift

    out_p = Path("results/paired_session/rerun_radisson_drift.json")
    out_p.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info("All rerun tasks finished and saved to %s", out_p)

if __name__ == "__main__":
    asyncio.run(main())
