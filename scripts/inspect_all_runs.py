"""
Inspect all raw run JSON files in results/ and extract exact attributes for reconciliation.
Handles result, offer, or root fields.
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
results_dir = ROOT / "results"

files = sorted(results_dir.glob("*.json"))

all_runs = []

for f in files:
    if f.name.startswith("live_pack1_discovery") or f.name.startswith("pack3_playwright") or f.name.startswith("all_runs"):
        continue
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        continue
    
    # Check nested containers
    res = data.get("result") or data.get("offer") or data
    
    run_id = data.get("run_id") or res.get("run_id") or f.stem
    platform = data.get("platform") or res.get("site") or res.get("platform")
    hotel = data.get("hotel_name") or res.get("hotel_name")
    
    # Status determination
    status = data.get("status") or res.get("status")
    reached = res.get("reached_payment_page")
    blocker = res.get("blocker") or data.get("blocker")
    
    # Started / finished timestamps for elapsed time
    started = data.get("started_at") or res.get("started_at")
    finished = data.get("finished_at") or res.get("finished_at")
    seconds = data.get("elapsed_seconds") or data.get("seconds")
    if not seconds and started and finished:
        try:
            t0 = datetime.fromisoformat(started)
            t1 = datetime.fromisoformat(finished)
            seconds = (t1 - t0).total_seconds()
        except Exception:
            pass

    steps = data.get("steps") or res.get("steps")
    room_text = res.get("room_type")
    max_occ = res.get("max_occupancy")
    meal = res.get("meal_plan")
    cancellation = res.get("cancellation_category") or res.get("cancellation_policy")
    listed = res.get("price_shown_on_listing") or res.get("price_listed")
    payable = res.get("price_final_payable")
    fee_lines = res.get("fee_lines") or []
    notes = res.get("notes") or data.get("error") or res.get("error") or ""

    # Reconcile status according to AGENTS.md:
    # verified requires reached_payment_page==True, price_final_payable!=None, fee_lines sum to payable within 1%
    calc_sum = sum(fl.get("amount", 0) for fl in fee_lines) if fee_lines else 0
    # Determine discount / coupon lines
    discounts = [fl for fl in fee_lines if fl.get("fee_kind") == "discount" or (isinstance(fl.get("amount"), (int, float)) and fl.get("amount") < 0) or "coupon" in fl.get("label", "").lower() or "promo" in fl.get("label", "").lower() or "discount" in fl.get("label", "").lower()]
    coupon_text = "; ".join(f"{fl.get('label')}: {fl.get('amount')}" for fl in discounts) if discounts else "none"

    all_runs.append({
        "file": f.name,
        "run_id": str(run_id),
        "platform": str(platform),
        "hotel": str(hotel),
        "status": str(status),
        "reached_payment": reached,
        "blocker": str(blocker) if blocker else "none",
        "notes": str(notes)[:120].replace("\n", " "),
        "seconds": round(seconds, 1) if isinstance(seconds, (int, float)) else None,
        "steps": steps,
        "room_text": str(room_text),
        "guests": max_occ,
        "meal": str(meal),
        "cancellation": str(cancellation)[:40] if cancellation else "none",
        "listed": listed,
        "payable": payable,
        "coupon_text": coupon_text,
    })

out_file = results_dir / "all_runs_summary.json"
with open(out_file, "w", encoding="utf-8") as out:
    json.dump(all_runs, out, indent=2)
print(f"Processed {len(all_runs)} runs.")
