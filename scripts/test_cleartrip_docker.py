import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook


async def main():
    t0 = time.time()
    hotel_name = "Radisson Blu Atria Bengaluru"
    params = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
    }
    print(f"Starting headless Cleartrip run in Linux Docker container for {hotel_name}...")
    res = await run_cleartrip_playbook(hotel_name, params, headless=True)
    elapsed = time.time() - t0

    reached_payment = res.get("reached_payment_page") is True
    payable = res.get("price_final_payable")
    fee_lines = res.get("fee_lines") or []
    fee_sum = sum(f.get("amount", 0.0) for f in fee_lines)
    reconciled = payable is not None and abs(payable - fee_sum) <= (0.01 * payable)
    occupancy = res.get("max_occupancy")

    status = "PASS" if reached_payment and reconciled else "FAIL"

    out = {
        "container_environment": "Linux Docker (Ubuntu noble, Playwright 1.49.0)",
        "hotel_name": hotel_name,
        "headless": True,
        "status": status,
        "elapsed_seconds": round(elapsed, 2),
        "reached_payment_page": reached_payment,
        "price_final_payable": payable,
        "fee_lines_sum": fee_sum,
        "fee_lines_reconciled": reconciled,
        "max_occupancy": occupancy,
        "cancellation_category": res.get("cancellation_category"),
        "meal_plan": res.get("meal_plan"),
        "rate_cohort": res.get("rate_cohort"),
        "raw_result": {k: v for k, v in res.items() if k not in ["listing_page_text", "payment_page_text"]},
    }

    with open("results/docker_test_result.json", "w") as f:
        json.dump(out, f, indent=2)

    print(f"DOCKER_RESULT: {status} in {elapsed:.2f}s, payable: {payable}, reconciled: {reconciled}")


if __name__ == "__main__":
    asyncio.run(main())
