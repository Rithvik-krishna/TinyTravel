#!/usr/bin/env python3
"""Record Fixture Script for TinyTravel.
Runs a full real investigation (the demo query) while logging every SSE event with real relative timings.
Saves:
  - fixtures/saved_run.json (ResultsResponse contract: mock=False, saved=True, saved_at, saved_run_label)
  - fixtures/saved_sse_script.json (ScriptFile contract: mock=False, saved=True, real timings, speed)
Copies local /evidence files to fixtures/evidence/ for portability.
Strips any potential secrets or private data.
Preserves blocked/unverified offers as-is.
"""
import argparse
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "api"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)
load_dotenv(override=True)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tinytravel.record_fixture")

from api.models import ResultsResponse
from api.events import ScriptFile
from api.services.orchestrator import run_search, get_search_queue
from api.services.tinyfish import get_balance

IST = timezone(timedelta(hours=5, minutes=30))


def sanitize_secrets_and_pii(data: any) -> any:
    """Recursively strip sensitive tokens, API keys, or private auth headers."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ("api_key", "secret", "password", "auth_token", "cookie", "session_id")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_secrets_and_pii(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_secrets_and_pii(item) for item in data]
    elif isinstance(data, str):
        # Scrub TinyFish api keys if present in strings
        sanitized = re.sub(r"tf_[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]", data)
        return sanitized
    return data


async def record(live: bool = False, yes_spend: bool = False, speed: float = 2.0) -> None:
    print("=" * 70)
    print("TinyTravel Fixture Recorder")
    print("=" * 70)

    if live:
        if not yes_spend:
            print("ERROR: --live requested without --yes-spend confirmation flag.")
            sys.exit(1)

        api_key = os.getenv("TINYFISH_API_KEY")
        if not api_key:
            print("ERROR: TINYFISH_API_KEY is not set in environment or .env.")
            sys.exit(1)

        balance = await get_balance()
        print(f"Checking wallet balance... Current balance: ${balance}")
        if balance is None or balance < 3.80:
            print(f"ERROR: Insufficient balance (${balance}). Estimated cost is ~$3.80. Aborting.")
            sys.exit(1)

        os.environ["DATA_MODE"] = "live"
        os.environ["TINYFISH_FAKE"] = "0"
        print(f"Mode: LIVE (TinyFish API Key present, Balance: ${balance:.2f})")
    else:
        os.environ["DATA_MODE"] = "fake"
        os.environ["TINYFISH_FAKE"] = "1"
        print("Mode: FAKE / DRY-RUN (no wallet spend, testing fixture creation pipeline)")

    # The canonical demo search query
    demo_request = {
        "destination": "Bengaluru",
        "area_hint": "HSR Layout / Koramangala",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "budget_per_night": 12000,
        "must_have": {
            "breakfast": True,
            "free_cancellation": True,
            "parking": False,
            "wifi": True,
        },
        "deal_mode": "best_value",
        "currency": "INR",
        "mock": False,
        "raw_text": "Bengaluru, 20-21 Nov 2026, 2 people, breakfast, free cancellation, under 12k",
    }

    search_id = f"saved_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    queue = get_search_queue(search_id)
    recorded_events = []
    start_time = time.monotonic()

    print(f"Search ID: {search_id}")
    print(f"Query: {demo_request['raw_text']}")
    print("-" * 70)

    async def collect_events():
        while True:
            item = await queue.get()
            if item is None:
                break
            recorded_events.append(item)
            t_ms = item.get("t_ms", 0)
            ev = item.get("event")
            edata = item.get("data", {})
            summary = ""
            if ev == "agent_started":
                summary = f"platform={edata.get('platform')}, hotel={edata.get('hotel')}"
            elif ev == "agent_done":
                summary = f"offer_id={edata.get('offer_id')}, status={edata.get('status')}"
            elif ev == "listings_found":
                summary = f"count={edata.get('count')}"
            elif ev == "hotels_grouped":
                summary = f"{len(edata.get('hotel_groups', []))} groups"
            print(f"[{t_ms/1000:6.2f}s] Event: {ev:<18} {summary}")

    collector_task = asyncio.create_task(collect_events())

    try:
        final_results = await run_search(search_id, demo_request)
    finally:
        await collector_task

    total_time_s = time.monotonic() - start_time
    print("-" * 70)
    print(f"Investigation completed in {total_time_s:.2f}s ({len(recorded_events)} SSE events captured).")

    # Metadata & Labeling
    now_ist = datetime.now(IST)
    iso_now = now_ist.isoformat()
    hh_mm = now_ist.strftime("%I:%M %p").lstrip("0")
    saved_run_label = f"Saved run, {hh_mm}"

    final_results["_meta"] = {
        "mock": False,
        "saved": True,
        "saved_at": iso_now,
        "saved_run_label": saved_run_label,
        "label": "saved",
        "note": f"Recorded real investigation ({len(final_results.get('offers', []))} offers) at {iso_now}",
    }

    # Ensure blocked / unverified offers are preserved as-is
    print("Offer statuses in results:")
    for o in final_results.get("offers", []):
        print(f"  - {o.get('offer_id')}: {o.get('site')} -> status={o.get('status')}, blocker={o.get('blocker')}, price={o.get('price_final_payable')}")

    # Copy local evidence files to fixtures/evidence/
    evidence_dir = ROOT / "evidence"
    fixtures_evidence_dir = ROOT / "fixtures" / "evidence"
    fixtures_evidence_dir.mkdir(parents=True, exist_ok=True)

    copied_evidence = 0
    for o in final_results.get("offers", []):
        for ev in o.get("evidence", []):
            ev_url = ev.get("url")
            if ev_url and ev_url.startswith("/evidence/"):
                fn = ev_url[len("/evidence/"):]
                src_path = evidence_dir / fn
                dst_path = fixtures_evidence_dir / fn
                if src_path.exists():
                    shutil.copy2(src_path, dst_path)
                    copied_evidence += 1
                    print(f"Copied evidence artifact: {fn} -> fixtures/evidence/{fn}")

    print(f"Total evidence artifacts copied: {copied_evidence}")

    # Sanitize any secrets/PII
    sanitized_results = sanitize_secrets_and_pii(final_results)
    sanitized_events = sanitize_secrets_and_pii(recorded_events)

    # Build saved_sse_script
    last_t_ms = sanitized_events[-1]["t_ms"] if sanitized_events else int(total_time_s * 1000)
    saved_sse_script = {
        "mock": False,
        "saved": True,
        "speed": speed,
        "speed_default": speed,
        "total_ms": last_t_ms,
        "events": sanitized_events,
    }

    # Strict Contract Validation
    print("Validating saved_run against ResultsResponse contract...")
    validated_run = ResultsResponse.model_validate(sanitized_results)
    print("  -> ResultsResponse: VALID!")

    print("Validating saved_sse_script against ScriptFile contract...")
    validated_script = ScriptFile.model_validate(saved_sse_script)
    print("  -> ScriptFile: VALID!")

    # Write files
    saved_run_path = ROOT / "fixtures" / "saved_run.json"
    saved_sse_path = ROOT / "fixtures" / "saved_sse_script.json"

    saved_run_path.write_text(json.dumps(sanitized_results, indent=2, ensure_ascii=False), encoding="utf-8")
    saved_sse_path.write_text(json.dumps(saved_sse_script, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {saved_run_path} ({saved_run_path.stat().st_size} bytes)")
    print(f"Wrote {saved_sse_path} ({saved_sse_path.stat().st_size} bytes)")
    print("=" * 70)
    print("Fixture recording SUCCESSFUL!")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Record full TinyTravel investigation as saved fixture.")
    parser.add_argument("--live", action="store_true", help="Execute live investigation with real TinyFish agents")
    parser.add_argument("--yes-spend", action="store_true", help="Confirm spending wallet credits for live execution")
    parser.add_argument("--speed", type=float, default=2.0, help="Default replay speed for SSE script (default 2.0)")
    args = parser.parse_args()

    asyncio.run(record(live=args.live, yes_spend=args.yes_spend, speed=args.speed))


if __name__ == "__main__":
    main()
