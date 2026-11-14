"""
Pack 1 Runner: Live Discovery & Checkout Verification with Spend Tracking.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from api.services.tinyfish import get_balance
from api.agents.discovery import discover
from api.agents.checkout import verify_offer

IST = timezone(timedelta(hours=5, minutes=30))


async def main():
    start_bal = await get_balance()
    print(f"[PACK 1] Starting TinyFish Balance: ${start_bal:.4f}")

    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "timeout_s": 600,
        "max_price": 8000,
    }

    print("\n--- Running Live Discovery on Cleartrip ---")
    try:
        cleartrip_listings = await discover("cleartrip", req, profile="lite")
        print(f"Cleartrip discovered {len(cleartrip_listings)} hotels.")
        with open("results/live_pack1_discovery_cleartrip.json", "w", encoding="utf-8") as f:
            json.dump(cleartrip_listings, f, indent=2)
    except Exception as e:
        print(f"Cleartrip discovery failed: {e}")
        cleartrip_listings = []

    bal_after_ct = await get_balance()
    print(f"Balance after Cleartrip discovery: ${bal_after_ct:.4f}")

    print("\n--- Running Live Discovery on Agoda ---")
    try:
        agoda_listings = await discover("agoda", req, profile="lite")
        print(f"Agoda discovered {len(agoda_listings)} hotels.")
        with open("results/live_pack1_discovery_agoda.json", "w", encoding="utf-8") as f:
            json.dump(agoda_listings, f, indent=2)
    except Exception as e:
        print(f"Agoda discovery failed: {e}")
        agoda_listings = []

    bal_after_ag = await get_balance()
    print(f"Balance after Agoda discovery: ${bal_after_ag:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
