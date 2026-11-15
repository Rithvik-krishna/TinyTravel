import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api"))

from api.agents.playbooks.cleartrip import run_cleartrip_playbook

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ct_dates_validation")
IST = timezone(timedelta(hours=5, minutes=30))

# 10 runs across 3 dates
VALIDATION_MATRIX = [
    # Hotel 1: Radisson Blu across 3 dates
    {"hotel": "radisson blu atria bengaluru", "display": "Radisson Blu Atria Bengaluru", "cin": "2026-11-20", "cout": "2026-11-21", "date_label": "Date 1 (Nov 20-21)"},
    {"hotel": "radisson blu atria bengaluru", "display": "Radisson Blu Atria Bengaluru", "cin": "2026-11-27", "cout": "2026-11-28", "date_label": "Date 2 (Nov 27-28)"},
    {"hotel": "radisson blu atria bengaluru", "display": "Radisson Blu Atria Bengaluru", "cin": "2026-12-15", "cout": "2026-12-16", "date_label": "Date 3 (Dec 15-16)"},
    # Hotel 2: Sterlings Mac across 2 dates
    {"hotel": "sterlings mac hotel bengaluru", "display": "Sterlings Mac Hotel", "cin": "2026-11-20", "cout": "2026-11-21", "date_label": "Date 1 (Nov 20-21)"},
    {"hotel": "sterlings mac hotel bengaluru", "display": "Sterlings Mac Hotel", "cin": "2026-11-27", "cout": "2026-11-28", "date_label": "Date 2 (Nov 27-28)"},
    # Hotel 3: La Marvella across 2 dates
    {"hotel": "la marvella", "display": "La Marvella", "cin": "2026-11-20", "cout": "2026-11-21", "date_label": "Date 1 (Nov 20-21)"},
    {"hotel": "la marvella", "display": "La Marvella", "cin": "2026-11-27", "cout": "2026-11-28", "date_label": "Date 2 (Nov 27-28)"},
    # Hotel 4: The Chancery Pavilion across 2 dates
    {"hotel": "the chancery pavilion", "display": "The Chancery Pavilion", "cin": "2026-11-20", "cout": "2026-11-21", "date_label": "Date 1 (Nov 20-21)"},
    {"hotel": "the chancery pavilion", "display": "The Chancery Pavilion", "cin": "2026-12-15", "cout": "2026-12-16", "date_label": "Date 3 (Dec 15-16)"},
    # Hotel 5: Bloomrooms
    {"hotel": "bloomrooms city centre", "display": "Bloomrooms @ City Centre", "cin": "2026-11-20", "cout": "2026-11-21", "date_label": "Date 1 (Nov 20-21)"},
]

out_dir = Path("results/recon/cleartrip_validation_dates")
out_dir.mkdir(parents=True, exist_ok=True)

async def run_single(item, idx):
    h = item["hotel"]
    dname = item["display"]
    cin = item["cin"]
    cout = item["cout"]
    dlabel = item["date_label"]

    req = {
        "destination": "Bengaluru",
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "offer_id": f"val_dates_{idx:02d}_{h[:6]}_{cin.replace('-', '')}",
    }

    t0 = time.perf_counter()
    logger.info(">>> [Run %d/10] Starting %s on %s...", idx, dname, dlabel)
    res = await run_cleartrip_playbook(h, req, timeout_s=90.0, max_steps=45, headless=True)
    elapsed = round(time.perf_counter() - t0, 2)

    page_dates = res.get("payment_page_dates", "")
    day_in = cin.split("-")[2]  # e.g. "20", "27", "15"
    day_out = cout.split("-")[2]
    # Check if page date includes requested day
    date_matches = (day_in in page_dates) and bool(page_dates)

    payable = res.get("price_final_payable")
    reached = res.get("reached_payment_page", False)
    status = res.get("status", "unverified")

    # Copy/ensure screenshot
    scr_src = Path(f"evidence/{req['offer_id']}_screenshot.png")
    scr_dst = out_dir / f"run_{idx}_{h[:10]}_{cin}.png"
    if scr_src.exists():
        scr_dst.write_bytes(scr_src.read_bytes())

    record = {
        "run_index": idx,
        "hotel_name": dname,
        "requested_check_in": cin,
        "requested_check_out": cout,
        "date_label": dlabel,
        "payment_page_dates": page_dates,
        "date_applied_matches": date_matches,
        "payment_page_reached": reached,
        "status": status,
        "seconds": elapsed,
        "price_final_payable": payable,
        "fee_lines": res.get("fee_lines", []),
        "room_type": res.get("room_type", ""),
        "cancellation_policy": res.get("cancellation_policy", ""),
        "screenshot": str(scr_dst),
    }

    logger.info("<<< [Run %d/10] Done: payable=%s page_dates='%s' matches=%s in %.2fs",
                idx, payable, page_dates, date_matches, elapsed)
    return record

async def main():
    records = []
    for idx, item in enumerate(VALIDATION_MATRIX, 1):
        rec = await run_single(item, idx)
        records.append(rec)
        await asyncio.sleep(2.0)

    out_file = Path("results/cleartrip_3dates_validation.json")
    out_file.write_text(json.dumps(records, indent=2), encoding="utf-8")
    logger.info("Validation completed. Saved to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
