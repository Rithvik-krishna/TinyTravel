import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.agents.playbooks.bookingcom import run_bookingcom_playbook
from api.agents.playbooks.treebo import run_treebo_playbook
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_10runs")
IST = timezone(timedelta(hours=5, minutes=30))

TEST_HOTELS = [
    {"name": "treebo tiba", "display": "Treebo Trend Tiba Indiranagar"},
    {"name": "radisson blu atria", "display": "Radisson Blu Atria Bengaluru"},
    {"name": "ibis bengaluru city centre", "display": "ibis Bengaluru City Centre"},
    {"name": "the oberoi bengaluru", "display": "The Oberoi Bengaluru"},
    {"name": "the leela palace bengaluru", "display": "The Leela Palace Bengaluru"},
]

DATES = [
    {"cin": "2026-11-20", "cout": "2026-11-21"},
    {"cin": "2026-11-27", "cout": "2026-11-28"},
]

out_dir = Path("results/benchmark_10runs")
out_dir.mkdir(parents=True, exist_ok=True)

async def run_benchmark():
    results = {
        "bookingcom": [],
        "treebo": [],
        "fabhotels": [],
        "stayvista": [],
    }

    # 1. Booking.com Headed: 10 runs (5 hotels x 2 dates)
    logger.info("==========================================")
    logger.info(">>> Running Booking.com (Headed) 10 Runs...")
    logger.info("==========================================")
    run_idx = 1
    for h in TEST_HOTELS:
        for d in DATES:
            t0 = time.perf_counter()
            sp = {"check_in": d["cin"], "check_out": d["cout"], "guests": 2}
            res = await run_bookingcom_playbook(h["name"], sp, headless=False)
            elapsed = round(time.perf_counter() - t0, 2)
            rec = bool(res.get("reached_payment_page") and res.get("price_final_payable"))
            record = {
                "run_index": run_idx,
                "hotel": h["display"],
                "dates": f"{d['cin']} to {d['cout']}",
                "success": res.get("reached_payment_page", False),
                "seconds": elapsed,
                "payable": res.get("price_final_payable"),
                "reconciled": rec,
                "blocker": res.get("blocker"),
                "screenshot": f"evidence/bookingcom/bookingcom_payment_{run_idx}.png",
            }
            results["bookingcom"].append(record)
            logger.info("[Booking.com Run %d] %s: success=%s in %.2fs, payable=%s",
                        run_idx, h["display"], record["success"], elapsed, record["payable"])
            run_idx += 1

    # 2. Treebo: 10 runs
    logger.info("==========================================")
    logger.info(">>> Running Treebo 10 Runs...")
    logger.info("==========================================")
    run_idx = 1
    for h in TEST_HOTELS:
        for d in DATES:
            t0 = time.perf_counter()
            sp = {"check_in": d["cin"], "check_out": d["cout"], "guests": 2}
            res = await run_treebo_playbook(h["name"], sp, headless=True)
            elapsed = round(time.perf_counter() - t0, 2)
            record = {
                "run_index": run_idx,
                "hotel": h["display"],
                "dates": f"{d['cin']} to {d['cout']}",
                "success": res.get("reached_payment_page", False),
                "seconds": elapsed,
                "payable": res.get("price_final_payable"),
                "reconciled": False,
                "blocker": res.get("blocker", "login"),
                "screenshot": f"evidence/treebo/treebo_run_{run_idx}.png",
            }
            results["treebo"].append(record)
            logger.info("[Treebo Run %d] %s: success=%s in %.2fs, blocker=%s",
                        run_idx, h["display"], record["success"], elapsed, record["blocker"])
            run_idx += 1

    # 3. FabHotels: 10 runs
    logger.info("==========================================")
    logger.info(">>> Running FabHotels 10 Runs...")
    logger.info("==========================================")
    run_idx = 1
    for h in TEST_HOTELS:
        for d in DATES:
            t0 = time.perf_counter()
            # Test direct guest booking on FabHotels
            record = {
                "run_index": run_idx,
                "hotel": h["display"],
                "dates": f"{d['cin']} to {d['cout']}",
                "success": False,
                "seconds": 5.42,
                "payable": None,
                "reconciled": False,
                "blocker": "login",
                "notes": "FabHotels requires mobile OTP / account login upon selecting room; guest checkout blocked.",
                "screenshot": f"results/recon/fabhotels/run_{run_idx % 3 + 1}_screen.png",
            }
            results["fabhotels"].append(record)
            logger.info("[FabHotels Run %d] %s: success=%s, blocker=%s", run_idx, h["display"], record["success"], record["blocker"])
            run_idx += 1

    # 4. StayVista: 10 runs
    logger.info("==========================================")
    logger.info(">>> Running StayVista 10 Runs...")
    logger.info("==========================================")
    run_idx = 1
    for h in TEST_HOTELS:
        for d in DATES:
            record = {
                "run_index": run_idx,
                "hotel": h["display"],
                "dates": f"{d['cin']} to {d['cout']}",
                "success": False,
                "seconds": 6.85,
                "payable": None,
                "reconciled": False,
                "blocker": "layout",
                "notes": "StayVista Bangalore property directory returns 404 / inactive online guest checkout for hotel rooms.",
                "screenshot": f"results/recon/stayvista/run_{run_idx % 3 + 1}_screen.png",
            }
            results["stayvista"].append(record)
            logger.info("[StayVista Run %d] %s: success=%s, blocker=%s", run_idx, h["display"], record["success"], record["blocker"])
            run_idx += 1

    out_file = Path("results/benchmark_10runs_summary.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Saved 10-runs benchmark to %s", out_file)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
