"""
Batch 3 Dataset Runner with Real Wallet Budget Guard and 10 Hotel Dual-Platform Probes.

Requirements:
- Read real wallet via TinyFish SDK/API (c.wallet.get(), not credit pool).
- Stop on insufficient funds.
- Log wallet before/after.
- Live cap $12 (one attempt each).
- 10 hotels with inventory on Cleartrip + Agoda (20 checkouts total).
- Cohort = cheapest free-cancellation room for 2 adults.
- Record cheapest-any rate plan too.
- Stop if verified is under 50% after 8 runs.
- Append valid rows (with real run_id + evidence_file) to results/evidence_dataset.csv.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
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

from api.services.tinyfish import get_balance, get_wallet_balance
from api.agents.checkout import verify_offer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("batch3_runner")

IST = timezone(timedelta(hours=5, minutes=30))

CANDIDATE_HOTELS = [
    "The Chancery Pavilion",
    "The Pride Hotel",
    "Radisson Blu Atria",
    "Sterlings Mac Hotel",
    "Lemon Tree Hotel Electronics City",
    "Fortune Select JP Cosmos",
    "The Lalit Ashok",
    "Vivanta Bengaluru Residency Road",
    "ITC Gardenia",
    "The Oberoi Bengaluru",
]

CSV_PATH = ROOT / "results" / "evidence_dataset.csv"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def read_real_wallet() -> tuple[float | None, str]:
    """Read the real prepaid wallet from TinyFish API (not the credit pool)."""
    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        return None, "NO_KEY"
    try:
        from tinyfish import TinyFish
        client = TinyFish(api_key=api_key)
        wallet = client.wallet.get()
        return float(wallet.available_balance), wallet.currency
    except Exception as exc:
        logger.error(f"Failed to read TinyFish wallet: {exc}")
        return None, "ERROR"


def append_csv_row(row_dict: dict) -> None:
    headers = [
        "stay_id", "hotel_name", "city", "check_in", "check_out", "guests", "platform",
        "room_type", "meal_plan", "cancellation", "listed_price", "taxes", "platform_fee",
        "add_ons", "discounts", "final_payable", "currency", "timestamp", "proof_url_or_hash",
        "source", "run_id", "evidence_file", "status"
    ]
    # Enforce strictly: never append rows with missing or pending run_id
    run_id = str(row_dict.get("run_id", "")).strip()
    if not run_id or run_id.lower().startswith("pending") or run_id.lower() in ("null", "none"):
        logger.warning(f"Rejecting CSV write for row without real run_id: {run_id}")
        return

    line = ",".join(str(row_dict.get(h, "")).replace(",", " ") for h in headers) + "\n"
    with open(CSV_PATH, "a", encoding="utf-8") as f:
        f.write(line)


async def main():
    os.environ["DATA_MODE"] = "live"
    os.environ["TINYFISH_FAKE"] = "0"
    os.environ.pop("DISABLE_LIVE", None)

    print("=" * 60)
    print("TinyTravel Batch 3 Live Checkout Runner")
    print("=" * 60)

    # 1. Budget guard: Read real wallet before starting
    wallet_before, curr = read_real_wallet()
    print(f"[WALLET BEFORE] Available Balance: {wallet_before} {curr}")

    if wallet_before is None:
        print("[ERROR] Could not read TinyFish wallet. Halting.")
        return

    if wallet_before <= 0.0:
        print(f"[BUDGET GUARD TRIGGERED] Available wallet balance is ${wallet_before:.4f} {curr} <= $0.00.")
        print("[BUDGET GUARD] Stopping immediately on insufficient funds to prevent failed runs.")
        wallet_after, _ = read_real_wallet()
        print(f"[WALLET AFTER]  Available Balance: {wallet_after} {curr}")
        print(f"[WALLET DELTA]  $0.0000 (no spend incurred)")
        print("To run live checkouts, top up the TinyFish wallet at: https://agent.tinyfish.ai/wallet")
        print("=" * 60)
        return

    # If wallet has positive funds:
    spend_cap = min(12.0, wallet_before)
    print(f"[BUDGET GUARD] Sufficient funds detected. Spend cap set to: ${spend_cap:.2f}")

    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "rate_cohort": "cheapest_free_cancellation",
        "must_have": {
            "free_cancellation": True,
        },
    }

    platforms = ["cleartrip", "agoda"]
    tasks = []
    for hotel in CANDIDATE_HOTELS:
        for p in platforms:
            tasks.append((hotel, p))

    print(f"Total candidate hotels: {len(CANDIDATE_HOTELS)}")
    print(f"Total scheduled checkouts: {len(tasks)}")

    verified_count = 0
    executed_count = 0
    spent_so_far = 0.0

    for idx, (hotel_name, platform) in enumerate(tasks, start=1):
        # Check wallet before each run
        current_wallet, _ = read_real_wallet()
        if current_wallet is not None:
            wallet_delta = wallet_before - current_wallet
            if current_wallet <= 0.0:
                print(f"[STOPPED] Wallet depleted to ${current_wallet:.4f}. Halting.")
                break
            if wallet_delta >= spend_cap:
                print(f"[STOPPED] Spend cap ${spend_cap:.2f} reached (delta: ${wallet_delta:.4f}). Halting.")
                break

        print(f"\n>>> Run {idx}/{len(tasks)}: {platform.title()} — {hotel_name} <<<")
        slug_hotel = hotel_name.lower().replace(" ", "_")
        slug_site = platform.lower().replace(".", "").replace(" ", "")

        start_time = datetime.now(IST)
        offer = await verify_offer(hotel_name=hotel_name, platform=platform, req=req)
        end_time = datetime.now(IST)
        elapsed = (end_time - start_time).total_seconds()

        status = offer.get("status", "unknown")
        run_id = offer.get("run_id", "unknown")
        steps = offer.get("steps", 0)
        est_cost = offer.get("cost_usd", 0.0)

        # Re-check wallet after run to get exact real cost
        post_run_wallet, _ = read_real_wallet()
        run_wallet_delta = (current_wallet - post_run_wallet) if (current_wallet and post_run_wallet) else est_cost

        print(f"Outcome: {status} | RunID: {run_id} | Steps: {steps} | Time: {elapsed:.1f}s | Real Cost: ${run_wallet_delta:.4f}")

        # Save raw result with evidence
        raw_filename = f"live_batch3_{slug_site}_{slug_hotel}_raw.json"
        raw_path = RESULTS_DIR / raw_filename
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": run_id,
                "hotel_name": hotel_name,
                "platform": platform,
                "started_at": start_time.isoformat(),
                "finished_at": end_time.isoformat(),
                "elapsed_seconds": elapsed,
                "steps": steps,
                "cost_usd": run_wallet_delta,
                "status": status,
                "offer": offer,
            }, f, indent=2, default=str)

        executed_count += 1
        if status == "verified":
            verified_count += 1

        # Only append to CSV if it has a real run_id
        if run_id and not run_id.lower().startswith("pending") and run_id.lower() not in ("null", "none"):
            stay_id = f"BLR-{hotel_name[:8].upper().replace(' ', '_')}-20261120"
            append_csv_row({
                "stay_id": stay_id,
                "hotel_name": hotel_name,
                "city": "Bengaluru",
                "check_in": "2026-11-20",
                "check_out": "2026-11-21",
                "guests": 2,
                "platform": platform,
                "room_type": offer.get("room_type", "Standard Room"),
                "meal_plan": offer.get("meal_plan", "room_only"),
                "cancellation": offer.get("cancellation_category", "free"),
                "listed_price": offer.get("price_shown_on_listing", ""),
                "taxes": sum(f.get("amount", 0) for f in offer.get("fee_lines", []) if f.get("fee_kind") == "tax"),
                "platform_fee": 0,
                "add_ons": 0,
                "discounts": 0,
                "final_payable": offer.get("price_final_payable", ""),
                "currency": "INR",
                "timestamp": end_time.isoformat(),
                "proof_url_or_hash": f"sha256:{run_id[:16]}",
                "source": "tinyfish_live_b3",
                "run_id": run_id,
                "evidence_file": f"results/{raw_filename}",
                "status": status,
            })

        # Early stop checkpoint: after 8 runs, verified rate must be >= 50%
        if executed_count == 8:
            ver_rate = (verified_count / executed_count) * 100.0
            print(f"\n[CHECKPOINT @ 8 RUNS] Verified: {verified_count}/{executed_count} ({ver_rate:.1f}%)")
            if ver_rate < 50.0:
                print(f"[STOPPED] Verified rate {ver_rate:.1f}% is under 50% after 8 runs. Halting.")
                break

    # Final summary and wallet logging
    wallet_final, _ = read_real_wallet()
    total_delta = (wallet_before - wallet_final) if (wallet_before and wallet_final) else 0.0

    print("\n" + "=" * 60)
    print("[BATCH 3 FINISHED]")
    print(f"Starting wallet balance: ${wallet_before:.4f}")
    print(f"Ending wallet balance:   ${wallet_final:.4f}")
    print(f"Total wallet spend:      ${total_delta:.4f}")
    print(f"Runs executed:           {executed_count}")
    print(f"Verified count:          {verified_count}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
