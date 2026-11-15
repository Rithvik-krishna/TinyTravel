"""
Docker test runner for newly added passing site playbooks.
Executes headless inside a Linux container:
1. Cleartrip (Cleartrip Playbook)
2. Booking.com (Booking.com Playbook)
3. Treebo Hotels (Treebo Playbook)
Saves results to results/docker_passing_sites_test.json.
"""
import asyncio
import json
import logging
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook
from api.agents.playbooks.treebo import run_treebo_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("docker_test_runner")


async def test_playbook(name: str, runner_coro, hotel_name: str, params: dict) -> dict:
    t0 = time.perf_counter()
    logger.info(">>> Starting Docker container test for %s on %s...", name, hotel_name)
    try:
        res = await runner_coro(hotel_name, params, headless=True)
        elapsed = round(time.perf_counter() - t0, 2)

        reached_payment = res.get("reached_payment_page") is True
        payable = res.get("price_final_payable")
        fee_lines = res.get("fee_lines") or []
        fee_sum = round(sum(f.get("amount", 0.0) for f in fee_lines), 2)
        reconciled = payable is not None and abs(payable - fee_sum) <= (0.01 * payable)
        blocker = res.get("blocker")

        status = "PASS" if reached_payment and reconciled else "FAIL"

        return {
            "platform": name,
            "hotel_name": hotel_name,
            "status": status,
            "elapsed_seconds": elapsed,
            "reached_payment_page": reached_payment,
            "price_final_payable": payable,
            "fee_lines_sum": fee_sum,
            "fee_lines_reconciled": reconciled,
            "max_occupancy": res.get("max_occupancy"),
            "blocker": blocker,
            "verification_level": res.get("verification_level", "checkout"),
        }
    except Exception as e:
        elapsed = round(time.perf_counter() - t0, 2)
        logger.error("[%s] Docker test failed with exception: %s", name, e)
        return {
            "platform": name,
            "hotel_name": hotel_name,
            "status": "FAIL",
            "elapsed_seconds": elapsed,
            "reached_payment_page": False,
            "price_final_payable": None,
            "fee_lines_sum": 0.0,
            "fee_lines_reconciled": False,
            "blocker": "other",
            "error": str(e),
            "verification_level": "checkout",
        }


async def main():
    params = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
    }

    tests = [
        ("Cleartrip", run_cleartrip_playbook, "Radisson Blu Atria Bengaluru"),
        ("Booking.com", run_bookingcom_playbook, "Treebo Tiba"),
        ("Treebo Hotels", run_treebo_playbook, "Treebo Tiba"),
    ]

    results = []
    for name, runner, hname in tests:
        res = await test_playbook(name, runner, hname, params)
        results.append(res)
        logger.info("[%s] Result: %s in %ss, payable=%s", name, res["status"], res["elapsed_seconds"], res["price_final_payable"])

    output_data = {
        "container_environment": "Linux Docker (Ubuntu noble, Playwright 1.49.0)",
        "executed_at": time.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "results": results,
    }

    out_file = ROOT / "results" / "docker_passing_sites_test.json"
    with open(out_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info("All Docker tests completed. Saved to results/docker_passing_sites_test.json")


if __name__ == "__main__":
    asyncio.run(main())
