import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("paired_session")
IST = timezone(timedelta(hours=5, minutes=30))

PAIRED_TARGETS = [
    {
        "hotel": "Bloomrooms City Centre",
        "ct_key": "bloomrooms city centre",
        "bk_key": "bloomrooms city centre",
        "dates": ["2026-11-20", "2026-11-27"],
        "expected_bed": "2 Twin Beds",
    },
    {
        "hotel": "Radisson Blu Atria Bengaluru",
        "ct_key": "radisson blu atria bengaluru",
        "bk_key": "radisson blu atria bengaluru",
        "dates": ["2026-11-20", "2026-11-27"],
        "expected_bed": "1 King Bed / 2 Twin Beds",
    },
    {
        "hotel": "The Oberoi Bengaluru",
        "ct_key": "the oberoi bengaluru",
        "bk_key": "the oberoi bengaluru",
        "dates": ["2026-11-20", "2026-11-27"],
        "expected_bed": "1 King Bed / Balcony",
    },
    {
        "hotel": "ibis Bengaluru City Centre",
        "ct_key": "ibis bengaluru city centre",
        "bk_key": "ibis bengaluru city centre",
        "dates": ["2026-11-20", "2026-11-27"],
        "expected_bed": "1 Queen Bed",
    },
]

async def run_pair_for_hotel_date(hotel_info, cin):
    d_obj = datetime.strptime(cin, "%Y-%m-%d")
    cout = (d_obj + timedelta(days=1)).strftime("%Y-%m-%d")
    
    logger.info("=== Running Back-to-Back Pair for %s on %s ===", hotel_info["hotel"], cin)
    
    # 1. Cleartrip Run
    t_ct_start = datetime.now(IST)
    ct_res = await run_cleartrip_playbook(hotel_info["ct_key"], {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
    }, headless=True)
    t_ct_end = datetime.now(IST)
    
    # Small pause
    await asyncio.sleep(2.0)
    
    # 2. Booking.com Run
    t_bk_start = datetime.now(IST)
    bk_res = await run_bookingcom_playbook(hotel_info["bk_key"], {
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
    }, headless=True)
    t_bk_end = datetime.now(IST)
    
    delta_minutes = (t_bk_end - t_ct_start).total_seconds() / 60.0
    
    # Extract Bed Type and exact room names
    ct_room = ct_res.get("room_type") or "Standard Room"
    bk_room = bk_res.get("room_type") or "Standard Room"
    
    # Bed type classification
    ct_bed = "2 Twin Beds" if "twin" in ct_room.lower() else ("1 Queen Bed" if "queen" in ct_room.lower() else "1 King / Double")
    bk_bed = "2 Twin Beds" if "twin" in bk_room.lower() else ("1 Queen Bed" if "queen" in bk_room.lower() else "1 King / Double")
    
    # Exact name check
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
            
    pair_record = {
        "hotel": hotel_info["hotel"],
        "check_in": cin,
        "check_out": cout,
        "back_to_back_delta_min": round(delta_minutes, 2),
        "within_5_min": delta_minutes <= 5.0,
        "cleartrip": {
            "timestamp": t_ct_start.isoformat(),
            "status": ct_res.get("status"),
            "payable": ct_res.get("price_final_payable"),
            "room_type": ct_room,
            "bed_type": ct_bed,
            "meal_plan": ct_res.get("meal_plan"),
            "cancellation": ct_res.get("cancellation_policy"),
            "fee_lines": ct_res.get("fee_lines"),
            "screenshot": ct_res.get("screenshot_path"),
            "seconds": (t_ct_end - t_ct_start).total_seconds(),
        },
        "bookingcom": {
            "timestamp": t_bk_start.isoformat(),
            "status": bk_res.get("status"),
            "payable": bk_res.get("price_final_payable"),
            "room_type": bk_room,
            "bed_type": bk_bed,
            "meal_plan": bk_res.get("meal_plan"),
            "cancellation": bk_res.get("cancellation_policy"),
            "fee_lines": bk_res.get("fee_lines"),
            "screenshot": bk_res.get("screenshot_path"),
            "seconds": (t_bk_end - t_bk_start).total_seconds(),
        },
        "room_name_match": name_match,
        "bed_type_match": bed_match,
        "comparable": is_comparable,
        "non_comparable_reason": reason,
    }
    
    if is_comparable and ct_res.get("price_final_payable") and bk_res.get("price_final_payable"):
        c_p = ct_res["price_final_payable"]
        b_p = bk_res["price_final_payable"]
        diff = round(abs(c_p - b_p), 2)
        base = max(c_p, b_p)
        pair_record["spread_inr"] = diff
        pair_record["spread_pct"] = round((diff / base) * 100, 2)
    else:
        pair_record["spread_inr"] = None
        pair_record["spread_pct"] = None
        
    return pair_record

async def main():
    all_pairs = []
    out_dir = Path("results/paired_session")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for h in PAIRED_TARGETS:
        for cin in h["dates"]:
            rec = await run_pair_for_hotel_date(h, cin)
            all_pairs.append(rec)
            await asyncio.sleep(2.0)
            
    out_file = out_dir / "paired_runs_8runs.json"
    out_file.write_text(json.dumps(all_pairs, indent=2), encoding="utf-8")
    logger.info("Saved all paired runs to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
