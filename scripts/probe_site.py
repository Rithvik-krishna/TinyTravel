#!/usr/bin/env python3
"""Probe site CLI tool.
Runs checkout verification agent against a specified hotel booking site.
Refuses to run live unless --yes-spend is explicitly supplied.
"""
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sys
import time

# Ensure api directory is in sys.path
repo_root = Path(__file__).resolve().parents[1]
api_dir = repo_root / "api"
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from agents.checkout import verify_offer

IST = timezone(timedelta(hours=5, minutes=30))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Probe a travel site for real payable hotel prices using TinyFish agent."
    )
    parser.add_argument(
        "--site",
        required=True,
        choices=["cleartrip", "agoda", "booking", "makemytrip", "goibibo", "easemytrip"],
        help="Target travel site platform",
    )
    parser.add_argument(
        "--hotel",
        required=True,
        help="Target hotel name (exact or canonical name)",
    )
    parser.add_argument(
        "--profile",
        choices=["lite", "stealth"],
        default="lite",
        help="Browser profile (default: lite)",
    )
    parser.add_argument(
        "--fake",
        action="store_true",
        help="Use deterministic canned probe response without calling TinyFish",
    )
    parser.add_argument(
        "--yes-spend",
        action="store_true",
        help="Acknowledge credit spend for live probe runs (~$0.30-$0.60 per run)",
    )
    parser.add_argument(
        "--url",
        help="Explicit search URL to bypass automatic platform URL generation",
    )
    parser.add_argument(
        "--destination",
        default="Bengaluru",
        help="Destination city (default: Bengaluru)",
    )
    parser.add_argument(
        "--check-in",
        default="2026-11-20",
        help="Check-in date YYYY-MM-DD (default: 2026-11-20)",
    )
    parser.add_argument(
        "--check-out",
        default="2026-11-21",
        help="Check-out date YYYY-MM-DD (default: 2026-11-21)",
    )
    parser.add_argument(
        "--guests",
        type=int,
        default=2,
        help="Number of guests (default: 2)",
    )
    parser.add_argument(
        "--rooms",
        type=int,
        default=1,
        help="Number of rooms (default: 1)",
    )
    return parser.parse_args()


async def main_async(args):
    # Safety gate: refuse live execution unless --yes-spend is passed
    if not args.fake and not args.yes_spend:
        sys.stderr.write(
            "\n[SAFETY BLOCK] Refusing to run live probe without --yes-spend.\n"
            "Live browser agents consume API credits (~$0.30-$0.60 per run).\n"
            "Options:\n"
            "  1. Test safely with canned data: pass --fake\n"
            "  2. Execute live agent: pass --yes-spend\n\n"
        )
        sys.exit(1)

    if args.fake:
        os.environ["TINYFISH_FAKE"] = "1"

    req = {
        "destination": args.destination,
        "check_in": args.check_in,
        "check_out": args.check_out,
        "guests": args.guests,
        "rooms": args.rooms,
        "must_have": {
            "breakfast": True,
            "free_cancellation": True,
        },
    }
    if args.url:
        req["url"] = args.url

    def on_stream(url: str):
        print(f"[Streaming Live] {url}")

    def on_progress(msg: str):
        print(f"[Progress] {msg}")

    print(f"Starting probe on {args.site} for hotel '{args.hotel}' (profile: {args.profile}, fake: {args.fake})...")
    start_time = time.perf_counter()

    try:
        offer = await verify_offer(
            platform=args.site,
            hotel_name=args.hotel,
            req=req,
            profile=args.profile,
            on_stream_url=on_stream,
            on_progress=on_progress,
        )
    except NotImplementedError as e:
        sys.stderr.write(f"\n[Platform Error] {e}\n")
        sys.exit(2)
    except Exception as e:
        sys.stderr.write(f"\n[Execution Error] {e}\n")
        sys.exit(3)

    elapsed_s = round(time.perf_counter() - start_time, 2)

    status = offer.get("status", "unknown")
    payable = offer.get("price_final_payable")
    payable_str = f"{payable:.2f}" if payable is not None else "N/A"
    leak = offer.get("fee_leak_pct")
    leak_str = f"{leak:.1f}%" if leak is not None else "N/A"
    steps = offer.get("steps", 0)
    cost = offer.get("cost_usd", 0.0)
    currency = offer.get("currency", "INR")

    # Compact summary output
    print("\n" + "=" * 80)
    print("PROBE SUMMARY")
    print(f"Site: {args.site} | Hotel: {args.hotel}")
    print(f"Status: {status} | Payable: {payable_str} {currency} | Leak: {leak_str}")
    print(f"Steps: {steps} | Duration: {elapsed_s}s | Cost: ${cost:.2f}")
    if offer.get("blocker"):
        print(f"Blocker: {offer['blocker']}")
    if offer.get("notes"):
        print(f"Notes: {offer['notes']}")
    print("=" * 80 + "\n")

    # Save full JSON to results/
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    out_file = results_dir / f"probe_{args.site}_{timestamp_slug}.json"
    out_file.write_text(json.dumps(offer, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Full JSON result saved to: {out_file}")


def main():
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
