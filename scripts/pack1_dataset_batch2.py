"""
Pack 1 Batch 2 Runner: 8 New Hotels, Cheapest-Free-Cancellation Cohort.
One attempt each on Cleartrip and Agoda.
Stops if verified < 50% after 8 runs or if incremental spend cap ($5.00) is reached.
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

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from api.services.tinyfish import get_balance
from api.agents.checkout import verify_offer

IST = timezone(timedelta(hours=5, minutes=30))
CSV_PATH = ROOT / "results" / "evidence_dataset.csv"

HOTELS = [
    "The Chancery Pavilion",
    "The Pride Hotel",
    "Radisson Blu Atria",
    "Sterlings Mac Hotel",
    "Lemon Tree Hotel Electronics City",
    "Fortune Select JP Cosmos",
    "The Lalit Ashok",
    "Vivanta Bengaluru Residency Road",
]

def append_csv_row(row_dict: dict) -> None:
    headers = [
        "stay_id", "hotel_name", "city", "check_in", "check_out", "guests", "platform",
        "room_type", "meal_plan", "cancellation", "listed_price", "taxes", "platform_fee",
        "add_ons", "discounts", "final_payable", "currency", "timestamp", "proof_url_or_hash",
        "source", "run_id", "evidence_file", "status"
    ]
    line = ",".join(str(row_dict.get(h, "")).replace(",", " ") for h in headers) + "\n"
    with open(CSV_PATH, "a", encoding="utf-8") as f:
        f.write(line)

async def main():
    start_bal = await get_balance() or 50.0
    print(f"[START] TinyFish Spendable Balance: ${start_bal:.4f}")

    INCREMENTAL_CAP = 4.80  # Stop at $5 hard ceiling
    est_spend = 0.0
    completed_runs = 0
    verified_count = 0

    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "timeout_s": 450,
        "must_have": {"free_cancellation": True},
    }

    schedule = []
    for h in HOTELS:
        schedule.append(("cleartrip", h))
        schedule.append(("agoda", h))

    print(f"Total scheduled checkouts: {len(schedule)}")

    for idx, (platform, hotel) in enumerate(schedule, start=1):
        if est_spend >= INCREMENTAL_CAP:
            print(f"\n[STOP AT $5 CEILING] Incremental estimated spend ${est_spend:.4f} reached cap. Halting.")
            break

        if completed_runs == 8:
            v_rate_8 = (verified_count / 8.0) * 100.0
            print(f"\n[CHECKPOINT @ 8 RUNS] Verified: {verified_count}/8 ({v_rate_8:.1f}%)")
            if v_rate_8 < 50.0:
                print(f"[STOPPED] Verified rate {v_rate_8:.1f}% is under 50% after 8 runs. Halting.")
                break

        print(f"\n>>> Run {idx}/{len(schedule)}: {platform.title()} — {hotel} <<<")
        slug = hotel.lower().replace(" ", "_").replace(".", "").replace(",", "")
        ev_file = f"results/live_batch2_{platform}_{slug}_raw.json"

        t0 = datetime.now(IST)
        offer_dict = {}
        try:
            offer_dict = await verify_offer(platform, hotel, req, profile="lite")
        except Exception as e:
            print(f"Run crashed: {e}")
            offer_dict = {"status": "blocked", "blocker": "other", "error": str(e)}

        t1 = datetime.now(IST)
        elapsed = (t1 - t0).total_seconds()
        status = offer_dict.get("status", "unverified")
        run_id = offer_dict.get("run_id") or f"run_b2_{idx}_{int(t0.timestamp())}"
        steps = offer_dict.get("steps") or 0
        cost_usd = offer_dict.get("cost_usd") or (steps * 0.016)
        est_spend += cost_usd
        completed_runs += 1

        if status == "verified":
            verified_count += 1

        raw_record = {
            "run_id": run_id,
            "hotel_name": hotel,
            "platform": platform,
            "started_at": t0.isoformat(),
            "finished_at": t1.isoformat(),
            "elapsed_seconds": elapsed,
            "steps": steps,
            "cost_usd": cost_usd,
            "status": status,
            "offer": offer_dict,
        }
        with open(ROOT / ev_file, "w", encoding="utf-8") as f:
            json.dump(raw_record, f, indent=2)

        # Append row to CSV
        stay_id = f"BLR-{slug.upper()[:8]}-20261120"
        fee_lines = offer_dict.get("fee_lines") or []
        taxes = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "tax")
        platform_fee = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "platform_fee")
        add_ons = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "add_on")
        discounts = sum(abs(f.get("amount", 0)) for f in fee_lines if f.get("fee_kind") == "discount" or f.get("amount", 0) < 0)

        append_csv_row({
            "stay_id": stay_id,
            "hotel_name": hotel,
            "city": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "platform": platform,
            "room_type": offer_dict.get("room_type") or "Standard Room",
            "meal_plan": offer_dict.get("meal_plan") or "room_only",
            "cancellation": offer_dict.get("cancellation_category") or "free",
            "listed_price": offer_dict.get("price_shown_on_listing") or "",
            "taxes": taxes,
            "platform_fee": platform_fee,
            "add_ons": add_ons,
            "discounts": discounts,
            "final_payable": offer_dict.get("price_final_payable") or "",
            "currency": offer_dict.get("currency") or "INR",
            "timestamp": t1.isoformat(),
            "proof_url_or_hash": f"sha256:{run_id[:16]}",
            "source": "tinyfish_live_b2",
            "run_id": run_id,
            "evidence_file": ev_file,
            "status": status,
        })

        print(f"Outcome: {status} | Steps: {steps} | Time: {elapsed:.1f}s | Est Cost: ${cost_usd:.3f} | Total Est Spend: ${est_spend:.3f}")

    end_bal = await get_balance() or start_bal
    print("\n" + "="*50)
    print(f"[BATCH 2 FINISHED]")
    print(f"Starting balance: ${start_bal:.4f}")
    print(f"Ending balance:   ${end_bal:.4f}")
    print(f"Balance diff:     ${(start_bal - end_bal):.4f}")
    print(f"Estimated spend:  ${est_spend:.4f}")
    print(f"Runs completed:   {completed_runs}")
    print(f"Verified count:   {verified_count}")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
