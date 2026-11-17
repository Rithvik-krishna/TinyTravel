import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

async def check():
    cin = "2026-11-20"
    cout = "2026-11-21"
    
    # Cleartrip Taj West End
    ct_taj = await run_cleartrip_playbook("taj west end", {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "catalog_only": True
    }, headless=True)
    print("Cleartrip Taj West End rates:")
    for r in ct_taj.get("rates", [])[:5]:
        print(f"  btn_idx={r.get('button_index')}: {r.get('room_name')} | {r.get('meal_plan')} | Total={r.get('total_price')}")

    # Booking Taj West End
    bk_taj = await run_bookingcom_playbook("taj west end", {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "catalog_only": True
    }, headless=False)
    print("\nBooking.com Taj West End rates:")
    for r in bk_taj.get("rates", [])[:5]:
        print(f"  blockId={r.get('blockId')}: {r.get('roomName')} | {r.get('mealPlan')} | Total={r.get('totalPrice')}")

if __name__ == "__main__":
    asyncio.run(check())
