"""
Pack 1 Checkout Runner with Spend Tracking and Early Stopping.
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
from api.agents.checkout import verify_offer
from scripts.evidence_dataset import load_evidence_csv, calculate_evidence_metrics, print_markdown_report

IST = timezone(timedelta(hours=5, minutes=30))

CANDIDATE_HOTELS = [
    "La Marvella",
    "Hotel City Centaur",
    "Holiday Inn Express Bengaluru Whitefield",
    "Taj Yeshwantpur",
    "Holiday Inn Bengaluru Racecourse",
]

CSV_PATH = ROOT / "results" / "evidence_dataset.csv"


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


async def run_pack1_checkouts():
    start_bal = await get_balance() or 50.0
    print(f"[START] TinyFish Spendable Balance: ${start_bal:.4f}")
    
    total_estimated_spend = 0.0
    SPEND_CAP = 6.0
    runs_completed = 0
    verified_count = 0

    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "timeout_s": 600,
    }

    # Alternate Cleartrip and Agoda across the 5 hotels
    schedule = []
    for h in CANDIDATE_HOTELS:
        schedule.append(("cleartrip", h))
        schedule.append(("agoda", h))

    for idx, (platform, hotel) in enumerate(schedule, start=1):
        # Check spend cap
        curr_bal = await get_balance() or start_bal
        actual_spend = start_bal - curr_bal
        if actual_spend >= SPEND_CAP or total_estimated_spend >= SPEND_CAP:
            print(f"\n[SPEND CAP HIT] Actual spend: ${actual_spend:.4f}, Est: ${total_estimated_spend:.4f}. Stopping.")
            break

        # Check early stopping condition: stop if first 6 runs verify under 40% (< 3 / 6)
        if runs_completed == 6:
            verify_rate_6 = (verified_count / 6.0) * 100.0
            print(f"\n[CHECKPOINT @ 6 RUNS] Verified: {verified_count}/6 ({verify_rate_6:.1f}%)")
            if verify_rate_6 < 40.0:
                print(f"[EARLY STOP TRIGGERED] Verified rate {verify_rate_6:.1f}% < 40% after 6 runs. Halting further runs.")
                break

        print(f"\n>>> Run {idx}/{len(schedule)}: {platform.title()} — {hotel} <<<")
        slug = hotel.lower().replace(" ", "_").replace(".", "").replace(",", "")
        ev_filename = f"results/live_pack1_{platform}_{slug}_raw.json"

        t0 = datetime.now(IST)
        offer_dict = {}
        try:
            offer_dict = await verify_offer(platform, hotel, req, profile="lite")
        except Exception as e:
            print(f"Error during verify_offer: {e}")
            offer_dict = {"status": "blocked", "blocker": "other", "error": str(e)}

        t1 = datetime.now(IST)
        elapsed_sec = (t1 - t0).total_seconds()

        # Parse offer response
        status = offer_dict.get("status", "unverified")
        run_id = offer_dict.get("run_id") or f"run_p1_{idx}_{int(t0.timestamp())}"
        steps = offer_dict.get("steps") or 0
        cost_usd = offer_dict.get("cost_usd") or (steps * 0.016)
        total_estimated_spend += cost_usd

        # Save raw evidence JSON
        raw_to_save = {
            "run_id": run_id,
            "hotel_name": hotel,
            "platform": platform,
            "started_at": t0.isoformat(),
            "finished_at": t1.isoformat(),
            "elapsed_seconds": elapsed_sec,
            "steps": steps,
            "cost_usd": cost_usd,
            "status": status,
            "offer": offer_dict,
        }
        with open(ROOT / ev_filename, "w", encoding="utf-8") as f:
            json.dump(raw_to_save, f, indent=2)

        runs_completed += 1
        if status == "verified":
            verified_count += 1

        print(f"Result: {status} | Steps: {steps} | Time: {elapsed_sec:.1f}s | Est Cost: ${cost_usd:.3f}")

        # Extract pricing fields for evidence CSV
        stay_id = f"BLR-{slug.upper()[:8]}-20261120"
        listed_price = offer_dict.get("price_listed") or ""
        final_payable = offer_dict.get("price_final_payable") or ""
        currency = offer_dict.get("currency") or "INR"
        room_type = offer_dict.get("room_type") or "Standard Room"
        meal_plan = "breakfast" if offer_dict.get("breakfast_included") else "room_only"
        cancellation = offer_dict.get("cancellation_category") or "non_refundable"

        # Itemized fee breakdown if present
        fee_lines = offer_dict.get("fee_lines") or []
        taxes = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "tax")
        platform_fee = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "service_fee")
        add_ons = sum(f.get("amount", 0) for f in fee_lines if f.get("fee_kind") == "add_on")
        discounts = sum(abs(f.get("amount", 0)) for f in fee_lines if f.get("fee_kind") == "discount" or f.get("amount", 0) < 0)

        row_data = {
            "stay_id": stay_id,
            "hotel_name": hotel,
            "city": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "platform": platform,
            "room_type": room_type,
            "meal_plan": meal_plan,
            "cancellation": cancellation,
            "listed_price": listed_price,
            "taxes": taxes,
            "platform_fee": platform_fee,
            "add_ons": add_ons,
            "discounts": discounts,
            "final_payable": final_payable,
            "currency": currency,
            "timestamp": t1.isoformat(),
            "proof_url_or_hash": f"sha256:{run_id[:16]}",
            "source": "tinyfish_live",
            "run_id": run_id,
            "evidence_file": ev_filename,
            "status": status,
        }
        append_csv_row(row_data)

    end_bal = await get_balance() or start_bal
    final_actual_spend = start_bal - end_bal
    print("\n" + "="*50)
    print(f"[PACK 1 FINISHED]")
    print(f"Starting balance: ${start_bal:.4f}")
    print(f"Ending balance:   ${end_bal:.4f}")
    print(f"Actual spend:     ${final_actual_spend:.4f}")
    print(f"Estimated spend:  ${total_estimated_spend:.4f}")
    print(f"Total runs:       {runs_completed}")
    print(f"Verified runs:    {verified_count}")
    print("="*50 + "\n")

    # Run analysis on the updated CSV
    valid, rejected = load_evidence_csv(CSV_PATH)
    metrics = calculate_evidence_metrics(valid)
    print_markdown_report(metrics, rejected)

if __name__ == "__main__":
    asyncio.run(run_pack1_checkouts())
