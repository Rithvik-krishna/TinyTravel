"""
Volatility Probe: La Marvella on Agoda (Attempt 3).
Executed >=30 min after Run 2 (13:11 IST).
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

from api.agents.checkout import verify_offer

IST = timezone(timedelta(hours=5, minutes=30))

async def main():
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "timeout_s": 450,
    }

    t0 = datetime.now(IST)
    print(f"Starting Agoda La Marvella Volatility Run 3 at {t0.isoformat()}...")
    res = await verify_offer("agoda", "La Marvella", req, profile="lite")
    t1 = datetime.now(IST)
    elapsed = (t1 - t0).total_seconds()
    
    out_file = ROOT / "results" / "volatility_agoda_la_marvella_run3_raw.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "run_id": res.get("run_id"),
            "started_at": t0.isoformat(),
            "finished_at": t1.isoformat(),
            "elapsed_seconds": elapsed,
            "offer": res,
        }, f, indent=2)

    print(f"Finished: status={res.get('status')} | payable={res.get('price_final_payable')} | time={elapsed:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
