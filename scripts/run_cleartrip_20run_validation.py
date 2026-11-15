"""
20-Run Validation of Cleartrip Playbook on 10 NEW Hotels across 2 stay dates.
Hotels:
- Budget: Bloomrooms City Centre, FabHotel Ivory Pearl, Treebo Tiba, Hotel Maurya
- Mid-range: Ibis Bengaluru City Centre, Lemon Tree Premier Electronics City, Fortune Select JP Cosmos
- 5-Star: The Oberoi Bengaluru, The Leela Palace Bengaluru, Taj West End

Stay Dates:
- Date A: 2026-11-20 to 2026-11-21
- Date B: 2026-12-05 to 2026-12-06

Also benchmarks Headed vs Headless execution.
Outputs results to results/cleartrip_20run_validation.json.
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ct_validation")

NEW_HOTELS = [
    {"name": "bloomrooms city centre", "tier": "Budget", "display_name": "Bloomrooms @ City Centre"},
    {"name": "fabhotel ivory pearl", "tier": "Budget", "display_name": "FabHotel Ivory Pearl Koramangala"},
    {"name": "treebo tiba", "tier": "Budget", "display_name": "Treebo Tiba"},
    {"name": "hotel maurya", "tier": "Budget", "display_name": "Hotel Maurya"},
    {"name": "ibis bengaluru city centre", "tier": "Mid-Range", "display_name": "ibis Bengaluru City Centre"},
    {"name": "lemon tree premier electronics city", "tier": "Mid-Range", "display_name": "Lemon Tree Premier Electronics City"},
    {"name": "fortune select jp cosmos", "tier": "Mid-Range", "display_name": "Fortune Select JP Cosmos"},
    {"name": "the oberoi bengaluru", "tier": "5-Star", "display_name": "The Oberoi Bengaluru"},
    {"name": "the leela palace bengaluru", "tier": "5-Star", "display_name": "The Leela Palace Bengaluru"},
    {"name": "taj west end", "tier": "5-Star", "display_name": "Taj West End"},
]

DATES = [
    {"check_in": "2026-11-20", "check_out": "2026-11-21", "label": "Date 1 (Nov 20-21)"},
    {"check_in": "2026-12-05", "check_out": "2026-12-06", "label": "Date 2 (Dec 05-06)"},
]

async def run_single_validation(hotel_info: dict, date_info: dict, run_idx: int, headless: bool = True) -> dict:
    hname = hotel_info["name"]
    dname = hotel_info["display_name"]
    tier = hotel_info["tier"]
    cin = date_info["check_in"]
    cout = date_info["check_out"]
    dlabel = date_info["label"]

    req = {
        "destination": "Bengaluru",
        "check_in": cin,
        "check_out": cout,
        "guests": 2,
        "offer_id": f"val_ct_{hname[:8]}_{cin.replace('-', '')}_{'headless' if headless else 'headed'}",
    }

    t0 = time.perf_counter()
    logger.info(">>> Running %s on %s (headless=%s)...", dname, dlabel, headless)
    try:
        res = await run_cleartrip_playbook(hname, req, timeout_s=90.0, max_steps=45, headless=headless)
    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        logger.error("Run failed for %s: %s", dname, exc)
        return {
            "run_index": run_idx,
            "hotel_name": dname,
            "tier": tier,
            "date_label": dlabel,
            "check_in": cin,
            "check_out": cout,
            "headless": headless,
            "success": False,
            "status": "unverified",
            "payment_page_reached": False,
            "seconds": elapsed,
            "price_final_payable": None,
            "fee_lines_reconcile": False,
            "fee_lines": [],
            "max_occupancy": None,
            "occupancy_correct": False,
            "room_type": "",
            "notes": f"Exception: {exc}",
        }

    elapsed = round(time.perf_counter() - t0, 2)
    reached_payment = bool(res.get("reached_payment_page", False))
    status = res.get("status", "unverified")
    payable = res.get("price_final_payable")
    fee_lines = res.get("fee_lines", [])
    max_occ = res.get("max_occupancy")
    occ_correct = (max_occ is not None and max_occ >= 2)

    # Check fee reconciliation (sum of lines matches payable within 1%)
    fee_sum = sum(fl.get("amount", 0.0) for fl in fee_lines if isinstance(fl, dict))
    reconciled = False
    if payable is not None and payable > 0:
        if abs(fee_sum - payable) / payable <= 0.01:
            reconciled = True

    is_success = reached_payment and (payable is not None) and (status == "verified")

    logger.info("<<< Finished %s in %.2fs: status=%s reached_payment=%s payable=%s reconciled=%s occ_correct=%s",
                dname, elapsed, status, reached_payment, payable, reconciled, occ_correct)

    return {
        "run_index": run_idx,
        "hotel_name": dname,
        "tier": tier,
        "date_label": dlabel,
        "check_in": cin,
        "check_out": cout,
        "headless": headless,
        "success": is_success,
        "status": status,
        "payment_page_reached": reached_payment,
        "seconds": elapsed,
        "steps": res.get("steps", 0),
        "price_shown_on_listing": res.get("price_shown_on_listing"),
        "price_final_payable": payable,
        "fee_lines_reconcile": reconciled,
        "fee_lines": fee_lines,
        "max_occupancy": max_occ,
        "occupancy_correct": occ_correct,
        "room_type": res.get("room_type", ""),
        "cancellation_policy": res.get("cancellation_policy", ""),
        "rate_cohort": res.get("rate_cohort", ""),
        "notes": res.get("notes", ""),
    }

async def main():
    runs = []
    run_idx = 1

    # 1. Execute 20 validation runs (10 hotels x 2 dates)
    for d_idx, d in enumerate(DATES):
        for h in NEW_HOTELS:
            # We'll run the first 2 runs of Date 1 in headed mode for headed vs headless benchmark
            use_headless = not (d_idx == 0 and run_idx in (1, 2))
            record = await run_single_validation(h, d, run_idx, headless=use_headless)
            runs.append(record)
            run_idx += 1
            await asyncio.sleep(2.0)

    # 2. Compare 3 baseline hotels against existing TinyFish payables
    baseline_hotels = [
        {"name": "radisson blu atria bengaluru", "tinyfish_payable": 11077.0, "display_name": "Radisson Blu Atria Bengaluru"},
        {"name": "sterlings mac hotel bengaluru", "tinyfish_payable": 38869.0, "display_name": "Sterlings Mac Hotel"},
        {"name": "la marvella", "tinyfish_payable": 11605.0, "display_name": "La Marvella"},
    ]
    baseline_comparisons = []
    for bh in baseline_hotels:
        req = {
            "destination": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "offer_id": f"baseline_cmp_{bh['name'][:8]}",
        }
        res = await run_cleartrip_playbook(bh["name"], req, timeout_s=90.0, max_steps=45)
        own_payable = res.get("price_final_payable")
        tf_payable = bh["tinyfish_payable"]
        diff = round(own_payable - tf_payable, 2) if own_payable is not None else None
        baseline_comparisons.append({
            "hotel_name": bh["display_name"],
            "tinyfish_payable": tf_payable,
            "own_playbook_payable": own_payable,
            "difference": diff,
            "match": abs(diff) <= 2.0 if diff is not None else False,
            "status": res.get("status"),
            "seconds": res.get("seconds"),
        })
        await asyncio.sleep(1.0)

    # Calculate summary metrics
    total_runs = len(runs)
    successes = [r for r in runs if r["success"]]
    payment_reached = [r for r in runs if r["payment_page_reached"]]
    reconciled_runs = [r for r in runs if r["fee_lines_reconcile"]]
    occ_correct_runs = [r for r in runs if r["occupancy_correct"]]
    avg_secs = sum(r["seconds"] for r in runs) / total_runs if total_runs else 0

    headed_runs = [r for r in runs if not r["headless"]]
    headless_runs = [r for r in runs if r["headless"]]
    avg_headed_secs = sum(r["seconds"] for r in headed_runs) / len(headed_runs) if headed_runs else 0
    avg_headless_secs = sum(r["seconds"] for r in headless_runs) / len(headless_runs) if headless_runs else 0

    tier_summary = {}
    for tier in ["Budget", "Mid-Range", "5-Star"]:
        t_runs = [r for r in runs if r["tier"] == tier]
        t_succ = [r for r in t_runs if r["success"]]
        tier_summary[tier] = {
            "runs": len(t_runs),
            "success_rate_pct": round((len(t_succ) / len(t_runs)) * 100, 1) if t_runs else 0,
            "avg_seconds": round(sum(r["seconds"] for r in t_runs) / len(t_runs), 2) if t_runs else 0,
        }

    summary = {
        "total_runs": total_runs,
        "success_rate_pct": round((len(successes) / total_runs) * 100, 1),
        "payment_page_reached_pct": round((len(payment_reached) / total_runs) * 100, 1),
        "fee_lines_reconcile_pct": round((len(reconciled_runs) / total_runs) * 100, 1),
        "occupancy_correct_pct": round((len(occ_correct_runs) / total_runs) * 100, 1),
        "avg_seconds": round(avg_secs, 2),
        "headed_vs_headless": {
            "headed_count": len(headed_runs),
            "avg_headed_seconds": round(avg_headed_secs, 2),
            "headless_count": len(headless_runs),
            "avg_headless_seconds": round(avg_headless_secs, 2),
        },
        "by_tier": tier_summary,
        "baseline_comparisons": baseline_comparisons,
    }

    out_file = ROOT / "results" / "cleartrip_20run_validation.json"
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runs": runs,
        "baseline_comparisons": baseline_comparisons,
    }
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")
    logger.info("Saved validation results to %s", out_file)
    print("\n=== VALIDATION SUMMARY ===")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
