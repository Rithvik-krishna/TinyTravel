import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

async def inspect():
    cin = "2026-11-20"
    cout = "2026-11-21"
    
    # 1. Cleartrip catalog for Oberoi
    ct_res = await run_cleartrip_playbook("the oberoi bengaluru", {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "catalog_only": True
    }, headless=True)
    print("Cleartrip Oberoi rates:")
    for r in ct_res.get("rates", []):
        print(f"  btn_idx={r.get('button_index')}: {r.get('room_name')} | {r.get('meal_plan')} | FreeCancel={r.get('free_cancellation')} | Total={r.get('total_price')}")

    # 2. Cleartrip catalog for ibis
    ct_ibis = await run_cleartrip_playbook("ibis bengaluru city centre", {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "catalog_only": True
    }, headless=True)
    print("\nCleartrip ibis rates:")
    for r in ct_ibis.get("rates", []):
        print(f"  btn_idx={r.get('button_index')}: {r.get('room_name')} | {r.get('meal_plan')} | FreeCancel={r.get('free_cancellation')} | Total={r.get('total_price')}")

if __name__ == "__main__":
    asyncio.run(inspect())
