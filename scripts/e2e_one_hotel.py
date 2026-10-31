#!/usr/bin/env python3
"""End-to-end Target Mode CLI Script for TinyTravel.
Runs single-hotel checkout verification across platforms (e.g. Cleartrip, Agoda, Booking.com).
Supports DATA_MODE=fake out of the box and --live --yes-spend for real runs.
"""
import argparse
import asyncio
from datetime import datetime
import json
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)
load_dotenv(override=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from api.models import ResultsResponse, SearchRequestOut
from api.services.orchestrator import run_search, get_search_queue


async def stream_and_display(search_id: str, queue: asyncio.Queue, start_time: float) -> None:
    """Consume and display real-time events from orchestrator queue."""
    while True:
        item = await queue.get()
        if item is None:
            break
        t_sec = (time.monotonic() - start_time)
        ev = item.get("event")
        data = item.get("data", {})

        if ev == "parsed":
            sr = data.get("search_request", {})
            print(f"[{t_sec:5.2f}s] [PARSED]          {sr.get('destination')} | {sr.get('check_in')} to {sr.get('check_out')} | {sr.get('guests')} guests | budget: INR {sr.get('budget_per_night')}")
        elif ev == "hotels_grouped":
            groups = data.get("hotel_groups", [])
            for g in groups:
                print(f"[{t_sec:5.2f}s] [HOTEL GROUPED]   {g.get('canonical_name')} ({g.get('match_status')}, {len(g.get('offer_ids', []))} platforms)")
        elif ev == "agent_started":
            print(f"[{t_sec:5.2f}s] [AGENT STARTED]   {data.get('platform'):12} -> {data.get('hotel')} (stream: {data.get('streaming_url')})")
        elif ev == "agent_progress":
            print(f"[{t_sec:5.2f}s] [PROGRESS]        {data.get('run_id')}: {data.get('step_text')}")
        elif ev == "agent_done":
            st = data.get("status")
            badge = "VERIFIED" if st == "verified" else ("BLOCKED" if st == "blocked" else "UNVERIFIED")
            print(f"[{t_sec:5.2f}s] [AGENT DONE]      {data.get('offer_id'):14} -> [{badge}]")
        elif ev == "ranking_ready":
            print(f"[{t_sec:5.2f}s] [RANKING READY]   Hero hotel spotlight: {data.get('hero_hotel_id')}")
        elif ev == "error":
            print(f"[{t_sec:5.2f}s] [ERROR]           {data.get('message')}")


async def main_async(args: argparse.Namespace) -> int:
    is_full = getattr(args, "full", False)
    platforms = [p.strip() for p in args.platforms.split(",")]

    # Calculate pre-flight cost estimate
    if is_full:
        num_disc = len(platforms)
        max_checkout = 3 * len(platforms)
        est_min_cost = (num_disc + 3) * 0.20
        est_max_cost = min(4.0, (num_disc + max_checkout) * 0.35)
        print("\n" + "=" * 70)
        print("FULL INVESTIGATION PRE-FLIGHT COST ESTIMATE")
        print("=" * 70)
        print(f"Mode                 : Full Investigation (Discovery -> Grouping -> Checkout)")
        print(f"Discovery Platforms  : {', '.join(platforms)} ({num_disc} discovery runs)")
        print(f"Target Selection     : Up to 3 hotel groups across discovered platforms")
        print(f"Estimated Total Runs : {num_disc} to {num_disc + max_checkout} runs")
        print(f"Estimated Cost Range : ${est_min_cost:.2f} - ${est_max_cost:.2f} USD (budget cap: $4.00 USD)")
        print(f"Concurrency Limit    : 3 parallel agent runs")
        print("=" * 70 + "\n")
    else:
        est_cost = len(platforms) * 0.30
        print("\n" + "=" * 70)
        print(f"TARGET MODE PRE-FLIGHT COST ESTIMATE: '{args.hotel}'")
        print("=" * 70)
        print(f"Platforms            : {', '.join(platforms)} ({len(platforms)} checkout runs)")
        print(f"Estimated Cost       : ~${est_cost:.2f} USD")
        print(f"Concurrency Limit    : 3 parallel agent runs")
        print("=" * 70 + "\n")

    # Mode setup
    if args.live:
        if not args.yes_spend:
            print("ERROR: --live mode requires --yes-spend flag to confirm TinyFish usage.", file=sys.stderr)
            return 1
        os.environ["DATA_MODE"] = "live"
        os.environ.pop("TINYFISH_FAKE", None)
        if "AGENT_TIMEOUT_S" not in os.environ:
            os.environ["AGENT_TIMEOUT_S"] = "600"
        print(">>> RUNNING IN LIVE MODE with real TinyFish agents <<<\n")
    else:
        os.environ["DATA_MODE"] = "fake"
        os.environ["TINYFISH_FAKE"] = "1"
        print(">>> RUNNING IN FAKE MODE (simulated speed) <<<\n")

    search_id = f"e2e_{int(time.time())}"

    req = {
        "destination": args.destination,
        "check_in": args.check_in,
        "check_out": args.check_out,
        "guests": args.guests,
        "rooms": args.rooms,
        "budget_per_night": args.budget,
        "deal_mode": args.deal_mode,
        "must_have": {
            "breakfast": True,
            "free_cancellation": True,
            "wifi": True,
            "parking": False,
        },
        "hotel_name": None if is_full else args.hotel,
        "platforms": platforms,
        "currency": "INR",
    }

    target = None if is_full else {
        "hotel_name": args.hotel,
        "platforms": platforms,
    }

    start_time = time.monotonic()
    queue = get_search_queue(search_id)

    if is_full:
        print(f"Initiating full investigation for '{args.destination}' across {', '.join(platforms)}...\n" + "-" * 70)
    else:
        print(f"Initiating target search for '{args.hotel}' across {', '.join(platforms)}...\n" + "-" * 70)

    # Launch display consumer and orchestrator runner concurrently
    display_task = asyncio.create_task(stream_and_display(search_id, queue, start_time))
    orchestrator_task = asyncio.create_task(run_search(search_id, req, target=target))

    results, _ = await asyncio.gather(orchestrator_task, display_task)
    total_time = time.monotonic() - start_time


    print("-" * 70)
    print(f"Completed in {total_time:.2f} seconds.")

    # Contract validation check
    try:
        ResultsResponse.model_validate(results)
        print("[CONTRACT CHECK] ResultsResponse contract validation: PASSED")
    except Exception as exc:
        print(f"[CONTRACT CHECK] Contract validation: FAILED ({exc})", file=sys.stderr)
        return 1

    # Print clean comparison table
    offers = results.get("offers", [])
    print("\n" + "=" * 70)
    print(f"TARGET RESULTS: {args.hotel}")
    print("=" * 70)
    print(f"{'Platform':<14} | {'Status':<10} | {'Shown':<10} | {'Final':<10} | {'Leak %':<8} | {'Score':<6}")
    print("-" * 70)
    for o in offers:
        site = o.get("site", "Unknown")
        st = o.get("status", "unverified")
        shown = f"INR {o.get('price_shown_on_listing'):,.0f}" if o.get("price_shown_on_listing") else "N/A"
        final = f"INR {o.get('price_final_payable'):,.0f}" if o.get("price_final_payable") else "N/A"
        leak = f"{o.get('fee_leak_pct'):+.1f}%" if o.get("fee_leak_pct") is not None else "N/A"
        tscore = o.get("transparency", {}).get("score")
        score_str = f"{tscore}/100" if tscore is not None else "N/A"
        print(f"{site:<14} | {st:<10} | {shown:<10} | {final:<10} | {leak:<8} | {score_str:<6}")

        # If live, save offer to fixtures/real/
        hname = o.get("hotel_name") or args.hotel or "hotel"
        hslug = hname.lower().replace(" ", "_")
        sslug = site.lower().replace(".", "").replace(" ", "")
        cslug = args.destination.lower().replace(" ", "_")
        if args.live:
            real_fixtures_dir = ROOT / "fixtures" / "real"
            real_fixtures_dir.mkdir(parents=True, exist_ok=True)
            if is_full or cslug != "bengaluru":
                offer_path = real_fixtures_dir / f"gate_{cslug}_{hslug}_{sslug}.json"
            else:
                offer_path = real_fixtures_dir / f"gate_{hslug}_{sslug}.json"
            offer_path.write_text(json.dumps(o, indent=2), encoding="utf-8")
            print(f"\n[SAVED OFFER] Saved processed offer to {offer_path}")

        # Verification audit details
        print("\n--- GATE AUDIT CHECKLIST ---")
        print(f"Hotel URL            : {o.get('hotel_url')}")
        print(f"Reached Payment Page : {o.get('reached_payment_page')}")
        print(f"Price Final Payable  : {o.get('price_final_payable')} {o.get('currency')}")
        print(f"Meal Plan            : {o.get('meal_plan')}")
        print(f"Cancellation Cat     : {o.get('cancellation_category')} ({o.get('cancellation_policy')})")

        fee_lines = o.get("fee_lines") or []
        fee_sum = sum(fl.get("amount", 0) for fl in fee_lines)
        payable = o.get("price_final_payable") or 0.0
        diff = abs(fee_sum - payable)
        tol = 0.01 * payable if payable else 0.0
        recon_ok = bool(payable and diff <= tol)
        print(f"Fee Lines Sum        : {fee_sum:,.2f} vs Payable: {payable:,.2f} (diff: {diff:.2f}, within 1%: {recon_ok})")

        price_trail = o.get("price_trail") or []
        steps_found = [pt.get("step") for pt in price_trail]
        print(f"Price Trail Steps    : {steps_found}")

        evidence_items = o.get("evidence") or []
        print(f"Evidence Count       : {len(evidence_items)}")
        for idx, ev in enumerate(evidence_items):
            print(f"  [{idx+1}] Type: {ev.get('type')} | Step: {ev.get('step')} | URL: {ev.get('url')} | Value: {ev.get('extracted_value')}")
        if o.get("listing_page_text"):
            print(f"Listing Page Text    : {o.get('listing_page_text')[:120]}...")
        if o.get("payment_page_text"):
            print(f"Payment Page Text    : {o.get('payment_page_text')[:120]}...")
        print("----------------------------\n")

    # Print verdicts
    verdicts = results.get("verdicts", {})
    overall = verdicts.get("overall", {})
    headlines = overall.get("headlines", {})
    print("-" * 70)
    print(f"Cheapest Verified : {overall.get('cheapest_verified')} ({headlines.get('cheapest_verified', '')})")
    print(f"Safe Cheapest     : {overall.get('safe_cheapest')} ({headlines.get('safe_cheapest', '')})")
    print(f"Best For You      : {overall.get('best_for_you')} ({headlines.get('best_for_you', '')})")
    print("=" * 70 + "\n")

    return 0


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end TinyTravel hotel checkout verification.")
    parser.add_argument("--hotel", default="La Marvella", help="Target hotel name")
    parser.add_argument("--platforms", default="Cleartrip,Agoda,Booking.com", help="Comma-separated platforms")
    parser.add_argument("--destination", default="Bengaluru", help="City name")
    parser.add_argument("--check-in", default="2026-11-20", help="Check-in date (YYYY-MM-DD)")
    parser.add_argument("--check-out", default="2026-11-21", help="Check-out date (YYYY-MM-DD)")
    parser.add_argument("--guests", type=int, default=2, help="Number of guests")
    parser.add_argument("--rooms", type=int, default=1, help="Number of rooms")
    parser.add_argument("--budget", type=float, default=12000.0, help="Budget per night")
    parser.add_argument("--deal-mode", default="best_value", help="Deal mode: best_value, lowest_price, most_transparent")
    parser.add_argument("--full", action="store_true", help="Run full investigation: discovery -> dedupe -> checkout")
    parser.add_argument("--live", action="store_true", help="Run against real platforms using TinyFish")
    parser.add_argument("--yes-spend", action="store_true", help="Acknowledge real spending for live mode")


    args = parser.parse_args()
    ret = asyncio.run(main_async(args))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(ret)


if __name__ == "__main__":
    main()
