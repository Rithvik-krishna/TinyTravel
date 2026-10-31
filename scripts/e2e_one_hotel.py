#!/usr/bin/env python3
"""End-to-end Target Mode CLI Script for TinyTravel.
Runs single-hotel checkout verification across platforms (e.g. Cleartrip, Agoda, Booking.com).
Supports DATA_MODE=fake out of the box and --live --yes-spend for real runs.
"""
import argparse
import asyncio
from datetime import datetime
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    # Mode setup
    if args.live:
        if not args.yes_spend:
            print("ERROR: --live mode requires --yes-spend flag to confirm TinyFish usage.", file=sys.stderr)
            return 1
        os.environ["DATA_MODE"] = "live"
        os.environ.pop("TINYFISH_FAKE", None)
        print(">>> RUNNING IN LIVE MODE with real TinyFish agents <<<")
    else:
        os.environ["DATA_MODE"] = "fake"
        os.environ["TINYFISH_FAKE"] = "1"
        print(">>> RUNNING IN FAKE MODE (simulated speed) <<<")

    search_id = f"e2e_{int(time.time())}"
    platforms = [p.strip() for p in args.platforms.split(",")]

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
        "hotel_name": args.hotel,
        "platforms": platforms,
        "currency": "INR",
    }

    target = {
        "hotel_name": args.hotel,
        "platforms": platforms,
    }

    start_time = time.monotonic()
    queue = get_search_queue(search_id)

    print(f"\nInitiating target search for '{args.hotel}' across {', '.join(platforms)}...\n" + "-" * 70)

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
    parser.add_argument("--live", action="store_true", help="Run against real platforms using TinyFish")
    parser.add_argument("--yes-spend", action="store_true", help="Acknowledge real spending for live mode")

    args = parser.parse_args()
    ret = asyncio.run(main_async(args))
    sys.exit(ret)


if __name__ == "__main__":
    main()
