import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from api.services.cohort_engine import run_3pass_cohort_verification

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rerun_cohort")
IST = timezone(timedelta(hours=5, minutes=30))

CASES = [
    ("Radisson Blu Atria Bengaluru", "2026-11-20", "2026-11-21"),
    ("La Marvella", "2026-11-20", "2026-11-21"),
]

async def main():
    results = []
    for hotel, cin, cout in CASES:
        logger.info("=== Testing 3-Pass Cohort Engine for: %s (%s to %s) ===", hotel, cin, cout)
        res = await run_3pass_cohort_verification(
            hotel_name=hotel,
            check_in=cin,
            check_out=cout,
            guests=2,
            headless=True,
        )
        logger.info("Result for %s: status=%s, stopped_before_checkout=%s, reason=%s",
                    hotel, res.get("status"), res.get("stopped_before_checkout"), res.get("reason"))
        results.append(res)

    out_file = Path("results/rerun_cohort_empty_stop.json")
    out_file.write_text(json.dumps(results, indent=2))
    logger.info("Saved rerun results to %s", out_file)

    print("\n" + "=" * 95)
    print(f"{'Hotel':<30} | {'Dates':<12} | {'Status':<16} | {'Stopped Pre-Checkout':<20} | {'Reason'}")
    print("-" * 95)
    for r in results:
        h = r["hotel_name"]
        d = f"{r['check_in']}..{r['check_out'][-2:]}"
        st = r["status"]
        stop = str(r.get("stopped_before_checkout", False))
        rsn = r.get("reason", "")[:45]
        print(f"{h:<30} | {d:<12} | {st:<16} | {stop:<20} | {rsn}")
    print("=" * 95)

if __name__ == "__main__":
    asyncio.run(main())
