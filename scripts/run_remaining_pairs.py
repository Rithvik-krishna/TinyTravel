import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

IST = timezone(timedelta(hours=5, minutes=30))

async def run_pair(h_name, ct_key, bk_key, cin, cout):
    t_ct_start = datetime.now(IST)
    ct = await run_cleartrip_playbook(ct_key, {'check_in': cin, 'check_out': cout, 'guests': 2}, headless=True)
    t_ct_end = datetime.now(IST)
    await asyncio.sleep(2.0)
    t_bk_start = datetime.now(IST)
    bk = await run_bookingcom_playbook(bk_key, {'check_in': cin, 'check_out': cout, 'guests': 2}, headless=True)
    t_bk_end = datetime.now(IST)
    delta_min = (t_bk_end - t_ct_start).total_seconds() / 60.0

    ct_room = ct.get("room_type") or "Standard Room"
    bk_room = bk.get("room_type") or "Standard Room"
    ct_bed = "2 Twin Beds" if "twin" in ct_room.lower() else ("1 Queen Bed" if "queen" in ct_room.lower() else "1 King / Double")
    bk_bed = "2 Twin Beds" if "twin" in bk_room.lower() else ("1 Queen Bed" if "queen" in bk_room.lower() else "1 King / Double")

    name_match = (ct_room.strip().lower() == bk_room.strip().lower()) or (
        "twin" in ct_room.lower() and "twin" in bk_room.lower() and "standard" in ct_room.lower() and "standard" in bk_room.lower()
    ) or (
        "superior" in ct_room.lower() and "superior" in bk_room.lower()
    )
    bed_match = (ct_bed == bk_bed)
    is_comparable = name_match and bed_match

    reason = None
    if not is_comparable:
        if not bed_match:
            reason = f"Bed type mismatch (Cleartrip: {ct_bed} vs Booking: {bk_bed})"
        else:
            reason = f"Room name mismatch (Cleartrip: '{ct_room}' vs Booking: '{bk_room}')"

    rec = {
        "hotel": h_name,
        "check_in": cin,
        "check_out": cout,
        "back_to_back_delta_min": round(delta_min, 2),
        "within_5_min": delta_min <= 5.0,
        "cleartrip": {
            "timestamp": t_ct_start.isoformat(),
            "status": ct.get("status"),
            "payable": ct.get("price_final_payable"),
            "room_type": ct_room,
            "bed_type": ct_bed,
            "meal_plan": ct.get("meal_plan"),
            "cancellation": ct.get("cancellation_policy"),
            "fee_lines": ct.get("fee_lines"),
            "screenshot": ct.get("screenshot_path"),
            "seconds": (t_ct_end - t_ct_start).total_seconds(),
        },
        "bookingcom": {
            "timestamp": t_bk_start.isoformat(),
            "status": bk.get("status"),
            "payable": bk.get("price_final_payable"),
            "room_type": bk_room,
            "bed_type": bk_bed,
            "meal_plan": bk.get("meal_plan"),
            "cancellation": bk.get("cancellation_policy"),
            "fee_lines": bk.get("fee_lines"),
            "screenshot": bk.get("screenshot_path"),
            "seconds": (t_bk_end - t_bk_start).total_seconds(),
        },
        "room_name_match": name_match,
        "bed_type_match": bed_match,
        "comparable": is_comparable,
        "non_comparable_reason": reason,
        "spread_inr": round(abs(ct.get("price_final_payable", 0) - bk.get("price_final_payable", 0)), 2) if is_comparable and ct.get("price_final_payable") and bk.get("price_final_payable") else None,
        "spread_pct": round(abs(ct.get("price_final_payable", 0) - bk.get("price_final_payable", 0)) / max(ct.get("price_final_payable", 1), bk.get("price_final_payable", 1)) * 100, 2) if is_comparable and ct.get("price_final_payable") and bk.get("price_final_payable") else None,
    }
    print("FINISHED:", json.dumps(rec, default=str))
    return rec

async def main():
    results = []
    # 1. The Oberoi Bengaluru 2026-11-20
    r1 = await run_pair('The Oberoi Bengaluru', 'the oberoi bengaluru', 'the oberoi bengaluru', '2026-11-20', '2026-11-21')
    results.append(r1)
    await asyncio.sleep(2.0)
    # 2. The Oberoi Bengaluru 2026-11-27
    r2 = await run_pair('The Oberoi Bengaluru', 'the oberoi bengaluru', 'the oberoi bengaluru', '2026-11-27', '2026-11-28')
    results.append(r2)
    await asyncio.sleep(2.0)
    # 3. ibis Bengaluru City Centre 2026-11-20
    r3 = await run_pair('ibis Bengaluru City Centre', 'ibis bengaluru city centre', 'ibis bengaluru city centre', '2026-11-20', '2026-11-21')
    results.append(r3)
    await asyncio.sleep(2.0)
    # 4. ibis Bengaluru City Centre 2026-11-27
    r4 = await run_pair('ibis Bengaluru City Centre', 'ibis bengaluru city centre', 'ibis bengaluru city centre', '2026-11-27', '2026-11-28')
    results.append(r4)

    Path("results/paired_session/remaining_pairs.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("ALL REMAINING SAVED!")

if __name__ == "__main__":
    asyncio.run(main())
