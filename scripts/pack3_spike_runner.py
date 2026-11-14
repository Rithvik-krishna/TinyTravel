"""
Pack 3 Spike Runner: Executes Cleartrip Playwright Playbook on 5 Pack 1 Hotels.
Records success rate, elapsed seconds, tokens/cost, and failure modes.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from scripts.playwright_cleartrip import run_cleartrip_playbook

CANDIDATE_HOTELS = [
    "La Marvella",
    "Hotel City Centaur",
    "Holiday Inn Express Bengaluru Whitefield",
    "Taj Yeshwantpur",
    "Holiday Inn Bengaluru Racecourse",
]

async def main():
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
    }

    results = []
    print("=" * 60)
    print("PACK 3: PLAYWRIGHT PLAYBOOK SPIKE (Cleartrip, 5 Hotels)")
    print("=" * 60)

    for idx, hotel in enumerate(CANDIDATE_HOTELS, start=1):
        t0 = datetime.now()
        res = await run_cleartrip_playbook(hotel, req, timeout_s=25.0)
        t1 = datetime.now()
        elapsed = (t1 - t0).total_seconds()
        
        record = {
            "hotel": hotel,
            "platform": "cleartrip",
            "status": res.get("status"),
            "blocker": res.get("blocker"),
            "error": res.get("error"),
            "seconds": res.get("seconds", elapsed),
            "steps": res.get("steps", 0),
            "llm_tokens": 0,
            "cost_usd": res.get("cost_usd", 0.0),
        }
        results.append(record)
        print(f"[{idx}/5] {hotel}: status={record['status']} | blocker={record['blocker']} | error={record['error']}")

    out_path = ROOT / "results" / "pack3_playwright_spike_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved Pack 3 spike results to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
