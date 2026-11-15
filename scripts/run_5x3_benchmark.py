"""
5x3 Benchmark Runner for Own Agent Playbooks (Cleartrip & Agoda).
Runs each playbook 5 times across 3 known hotels (30 runs total):
1. Radisson Blu Atria Bengaluru
2. Sterlings Mac Hotel
3. La Marvella

Measures:
- Success rate
- Elapsed seconds
- Correct occupancy (>= 2 adults)
- Failures / Blockers
Outputs structured JSON to results/own_agent_benchmark_results.json.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.agoda import run_agoda_playbook
from api.models import ProbeResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark")

HOTELS = [
    "Radisson Blu Atria Bengaluru",
    "Sterlings Mac Hotel",
    "La Marvella",
]

PLATFORMS = [
    "cleartrip",
    "agoda",
]

ITERATIONS = 5

async def run_single(platform: str, hotel_name: str, iteration: int) -> dict:
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "offer_id": f"bench_{platform}_{hotel_name.lower().replace(' ', '_')[:8]}_i{iteration}",
    }
    t0 = time.perf_counter()
    logger.info(">>> [%s] %s - Run %d/%d starting...", platform.upper(), hotel_name, iteration, ITERATIONS)

    try:
        if platform == "cleartrip":
            raw_res = await run_cleartrip_playbook(hotel_name, req, timeout_s=90.0, max_steps=45)
        elif platform == "agoda":
            raw_res = await run_agoda_playbook(hotel_name, req, timeout_s=90.0, max_steps=45)
        else:
            raise ValueError(f"Unknown platform {platform}")
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        logger.error("[%s] %s - Run %d failed with exception: %s", platform, hotel_name, iteration, exc)
        return {
            "platform": platform,
            "hotel_name": hotel_name,
            "iteration": iteration,
            "success": False,
            "status": "unverified",
            "blocker": "other",
            "reached_payment_page": False,
            "seconds": elapsed,
            "steps": 0,
            "max_occupancy": None,
            "correct_occupancy": False,
            "room_type": "",
            "price_final_payable": None,
            "fee_lines": [],
            "cancellation_policy": "",
            "notes": f"Exception: {exc}",
        }

    elapsed = round(time.perf_counter() - t0, 2)
    status = raw_res.get("status", "unverified")
    reached_payment = bool(raw_res.get("reached_payment_page", False))
    blocker = raw_res.get("blocker")
    max_occ = raw_res.get("max_occupancy")
    correct_occ = (max_occ is not None and max_occ >= 2)
    payable = raw_res.get("price_final_payable")
    steps = raw_res.get("steps", 0)

    # Success criteria: reached payment page with verified payable price
    is_success = reached_payment and payable is not None and status == "verified"

    logger.info(
        "<<< [%s] %s - Run %d finished in %.2fs: status=%s reached_payment=%s payable=%s occ=%s blocker=%s",
        platform.upper(), hotel_name, iteration, elapsed, status, reached_payment, payable, max_occ, blocker
    )

    return {
        "platform": platform,
        "hotel_name": hotel_name,
        "iteration": iteration,
        "success": is_success,
        "status": status,
        "blocker": blocker,
        "reached_payment_page": reached_payment,
        "seconds": elapsed,
        "steps": steps,
        "max_occupancy": max_occ,
        "correct_occupancy": correct_occ,
        "room_type": raw_res.get("room_type", ""),
        "meal_plan": raw_res.get("meal_plan", ""),
        "cancellation_policy": raw_res.get("cancellation_policy", ""),
        "price_shown_on_listing": raw_res.get("price_shown_on_listing"),
        "price_final_payable": payable,
        "cheapest_any_payable": raw_res.get("cheapest_any_payable"),
        "fee_lines": raw_res.get("fee_lines", []),
        "notes": raw_res.get("notes", ""),
    }


async def main():
    results_dir = ROOT / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / "own_agent_benchmark_results.json"

    all_runs = []
    
    # Run Agoda first (fast because of anti-bot challenge ~2-4s per run)
    for hotel in HOTELS:
        for i in range(1, ITERATIONS + 1):
            res = await run_single("agoda", hotel, i)
            all_runs.append(res)
            # Brief cool-down
            await asyncio.sleep(1.0)

    # Run Cleartrip (live browser checkout ~20-25s per run)
    for hotel in HOTELS:
        for i in range(1, ITERATIONS + 1):
            res = await run_single("cleartrip", hotel, i)
            all_runs.append(res)
            # Cool-down between browser sessions
            await asyncio.sleep(2.0)

    # Summary calculations
    summary = {}
    for platform in PLATFORMS:
        p_runs = [r for r in all_runs if r["platform"] == platform]
        summary[platform] = {}
        for hotel in HOTELS:
            h_runs = [r for r in p_runs if r["hotel_name"] == hotel]
            successes = [r for r in h_runs if r["success"]]
            correct_occs = [r for r in h_runs if r["correct_occupancy"]]
            avg_secs = sum(r["seconds"] for r in h_runs) / len(h_runs) if h_runs else 0
            blockers = list({r["blocker"] for r in h_runs if r["blocker"]})
            summary[platform][hotel] = {
                "runs": len(h_runs),
                "success_count": len(successes),
                "success_rate_pct": round((len(successes) / len(h_runs)) * 100, 1) if h_runs else 0,
                "avg_seconds": round(avg_secs, 2),
                "correct_occupancy_count": len(correct_occs),
                "blockers": blockers,
            }

        total_p_runs = len(p_runs)
        total_p_success = len([r for r in p_runs if r["success"]])
        summary[platform]["_overall"] = {
            "total_runs": total_p_runs,
            "success_rate_pct": round((total_p_success / total_p_runs) * 100, 1) if total_p_runs else 0,
            "avg_seconds": round(sum(r["seconds"] for r in p_runs) / total_p_runs, 2) if total_p_runs else 0,
            "correct_occupancy_rate_pct": round((len([r for r in p_runs if r["correct_occupancy"]]) / total_p_runs) * 100, 1) if total_p_runs else 0,
        }

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": all_runs,
    }

    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved benchmark results to %s", out_file)
    print("\n=== BENCHMARK SUMMARY ===")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
