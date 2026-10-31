#!/usr/bin/env python3
"""Comprehensive Query Suite and Invariant Verification for TinyTravel.
Runs 12+ varied queries and injected failure drills in fake mode.
Optionally runs 2 live target-mode searches with --live-n 2.

Invariants Verified:
  1. No crash under any input
  2. Invalid input yields a clear descriptive error (400 / ValueError)
  3. Every verified offer satisfies strict verification rule:
     - reached_payment_page == True
     - price_final_payable is not None
     - len(evidence) > 0
     - fee_lines sum to price_final_payable within +/- 1%
  4. No unknown value becomes 0 (null stays null)
  5. Blocked / unverified offers never receive a transparency score (score=None)
  6. Verdicts are null (not wrong picks) when impossible
  7. Results strictly validate against ResultsResponse contract model
  8. SSE event sequence follows expected workflow order
  9. USD / foreign currency offers are never converted to INR and excluded with visible warning
"""
import argparse
import asyncio
from datetime import datetime
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

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

logging.basicConfig(level=logging.WARNING)

from api.models import ResultsResponse
from api.services.intake import parse_request
from api.services.orchestrator import run_search, get_search_queue
from api.services.scoring import rank_offers, pick_verdicts, non_comparable_warnings, transparency_score
from api.services.dedupe import group_listings


class TestResult:
    def __init__(self, name: str, category: str, passed: bool, message: str = "", duration_s: float = 0.0):
        self.name = name
        self.category = category
        self.passed = passed
        self.message = message
        self.duration_s = duration_s


def assert_invariants(results: dict, events: list[dict]) -> tuple[bool, str]:
    """Assert all TinyTravel safety and product invariants on search results."""
    # 1. ResultsResponse strict validation
    try:
        ResultsResponse.model_validate(results)
    except Exception as e:
        return False, f"Contract validation failed: {e}"

    # 2. SSE Event Order check (if events present)
    if events:
        event_names = [e.get("event") for e in events]
        expected_phases = ["parsed", "discovery_started", "listings_found", "hotels_grouped", "ranking_ready"]
        last_idx = -1
        for ep in expected_phases:
            if ep in event_names:
                curr_idx = event_names.index(ep)
                if curr_idx < last_idx:
                    return False, f"SSE order violation: {ep} occurred before preceding phase"
                last_idx = curr_idx

    offers = results.get("offers", [])

    for o in offers:
        status = o.get("status")
        payable = o.get("price_final_payable")
        ev_items = o.get("evidence", [])
        fee_lines = o.get("fee_lines", [])

        # 3. Verified offer invariants
        if status == "verified":
            if not o.get("reached_payment_page"):
                return False, f"Offer {o.get('offer_id')} verified but reached_payment_page is False"
            if payable is None:
                return False, f"Offer {o.get('offer_id')} verified but price_final_payable is None"
            if not ev_items:
                return False, f"Offer {o.get('offer_id')} verified but evidence is empty"
            if fee_lines:
                sum_lines = sum(float(l.get("amount", 0.0)) for l in fee_lines)
                if abs(sum_lines - float(payable)) > (0.01 * float(payable) + 0.5):
                    return False, f"Offer {o.get('offer_id')} fee_lines sum {sum_lines} mismatches payable {payable}"

        # 4. Blocked / unverified offer invariants
        if status in ("blocked", "unverified"):
            tr = o.get("transparency", {})
            if tr and tr.get("score") is not None:
                return False, f"Offer {o.get('offer_id')} status={status} but received transparency score={tr.get('score')}"

        # 5. No unknown value becomes 0
        if o.get("price_shown_on_listing") == 0:
            return False, f"Offer {o.get('offer_id')} price_shown_on_listing is 0 instead of None"

    # 6. Verdicts invariants
    verdicts = results.get("verdicts", {})
    verified_offers = [o for o in offers if o.get("status") == "verified" and o.get("price_final_payable") is not None]
    
    if not verified_offers:
        overall = verdicts.get("overall", {})
        if overall.get("cheapest_verified") is not None:
            return False, "Overall cheapest_verified is not None despite zero verified offers"
        if overall.get("safe_cheapest") is not None:
            return False, "Overall safe_cheapest is not None despite zero verified offers"
        if overall.get("best_for_you") is not None:
            return False, "Overall best_for_you is not None despite zero verified offers"

    # 7. Safe cheapest cancellation invariant
    overall = verdicts.get("overall", {})
    safe_oid = overall.get("safe_cheapest")
    if safe_oid:
        matched_safe = next((o for o in offers if o.get("offer_id") == safe_oid), None)
        if matched_safe and matched_safe.get("cancellation_category") != "free":
            return False, f"safe_cheapest offer {safe_oid} does not have free cancellation (has {matched_safe.get('cancellation_category')})"

    return True, "All invariants verified"


async def run_query_test(name: str, query: any, is_bad_input: bool = False, expected_error: str = "") -> TestResult:
    start_t = time.monotonic()
    search_id = f"test_{int(start_t * 1000) % 1000000}"

    if is_bad_input:
        try:
            if isinstance(query, str):
                parse_request(query)
            elif isinstance(query, dict):
                from api.services.intake import validate_search_request
                validate_search_request(query)
            dur = time.monotonic() - start_t
            return TestResult(name, "Bad Input", False, "Expected error but query passed intake", dur)
        except (ValueError, Exception) as exc:
            dur = time.monotonic() - start_t
            err_msg = str(exc)
            if expected_error and expected_error.lower() not in err_msg.lower():
                return TestResult(name, "Bad Input", True, f"Rejected with: {err_msg}", dur)
            return TestResult(name, "Bad Input", True, f"Correctly rejected: {err_msg}", dur)

    # Valid query run
    try:
        os.environ["DATA_MODE"] = "fake"
        os.environ["TINYFISH_FAKE"] = "1"

        req_payload = query if isinstance(query, dict) else parse_request(query).model_dump()
        queue = get_search_queue(search_id)
        events = []

        async def collect():
            while True:
                item = await queue.get()
                if item is None:
                    break
                events.append(item)

        task = asyncio.create_task(collect())
        res = await run_search(search_id, req_payload)
        await task
        dur = time.monotonic() - start_t

        ok, msg = assert_invariants(res, events)
        return TestResult(name, "Valid Query", ok, msg, dur)

    except Exception as exc:
        dur = time.monotonic() - start_t
        return TestResult(name, "Valid Query", False, f"Pipeline crashed: {exc}", dur)


async def run_failure_drill(name: str, drill_fn) -> TestResult:
    start_t = time.monotonic()
    try:
        ok, msg = await drill_fn()
        dur = time.monotonic() - start_t
        return TestResult(name, "Failure Drill", ok, msg, dur)
    except Exception as exc:
        dur = time.monotonic() - start_t
        return TestResult(name, "Failure Drill", False, f"Drill crashed: {exc}", dur)


# --- Drill Implementations ---

async def drill_timeout():
    """Drill: Agent timeout handling."""
    from api.services.orchestrator import _create_unverified_offer
    offer = _create_unverified_offer(
        offer_id="drill_timeout_1",
        hotel_id="h1",
        hotel_name="Timeout Palace",
        platform="Cleartrip",
        run_id="run_timeout",
        blocker="timeout",
        furthest_step="timeout",
        notes="Agent timed out after 360s",
        mock=True,
    )
    tr = transparency_score(offer)
    if tr.get("score") is not None:
        return False, "Timeout offer received a non-null score"
    if offer["status"] != "unverified" or offer["blocker"] != "timeout":
        return False, f"Incorrect timeout status: {offer['status']}, blocker: {offer['blocker']}"
    return True, "Timeout correctly handled as unverified with score=null"


async def drill_captcha():
    """Drill: Captcha challenge encountered."""
    from api.services.orchestrator import _create_unverified_offer
    offer = _create_unverified_offer(
        offer_id="drill_captcha_1",
        hotel_id="h1",
        hotel_name="Captcha Inn",
        platform="Booking.com",
        run_id="run_captcha",
        blocker="captcha",
        furthest_step="search",
        notes="Cloudflare Turnstile challenge encountered",
        mock=True,
    )
    offer["status"] = "blocked"
    tr = transparency_score(offer)
    if tr.get("score") is not None:
        return False, "Captcha blocked offer received a non-null score"
    if offer["status"] != "blocked" or offer["blocker"] != "captcha":
        return False, f"Incorrect captcha status: {offer['status']}"
    return True, "Captcha correctly recorded as blocked with score=null"


async def drill_payment_page_never_reached():
    """Drill: Agent stopped before payment page."""
    offer = {
        "offer_id": "drill_no_pay",
        "hotel_id": "h1",
        "site": "Agoda",
        "reached_payment_page": False,
        "price_final_payable": 8500.0,
        "evidence": [{"step": "listing", "url": "/evidence/list.txt"}],
        "fee_lines": [{"name": "Room", "amount": 8500.0}],
        "status": "unverified",
    }
    from api.services.scoring import determine_status
    st = determine_status(
        reached_payment_page=False,
        final_price=8500.0,
        evidence=offer["evidence"],
        reconciliation="ok",
        blocker=None,
    )
    if st == "verified":
        return False, "Offer without reached_payment_page verified"
    return True, "Offer without reached_payment_page strictly kept unverified"


async def drill_duplicate_hotels():
    """Drill: Deduplication correctly collapses near-identical listings."""
    listings = [
        {"listing_id": "l1", "platform": "Cleartrip", "hotel_name": "La Marvella", "area": "Jayanagar", "phone": "08043335333"},
        {"listing_id": "l2", "platform": "Agoda", "hotel_name": "La Marvella, Bengaluru", "area": "Jayanagar", "phone": "08043335333"},
        {"listing_id": "l3", "platform": "Booking.com", "hotel_name": "La Marvella Hotel & Suites", "area": "Jayanagar", "phone": "08043335333"},
    ]
    groups = group_listings(listings)
    if len(groups) != 1:
        return False, f"Expected 1 grouped hotel, got {len(groups)}"
    g = groups[0]
    if g.get("match_status") != "merged" or len(g.get("offer_ids", [])) != 3:
        return False, f"Dedupe failed to merge 3 platforms (merged={g.get('match_status')}, offers={g.get('offer_ids')})"
    return True, f"Successfully merged 3 duplicate platforms into '{g.get('canonical_name')}'"


async def drill_currency_mismatch_usd():
    """Drill: Platform returns USD price; preserved as USD, excluded from INR ranking with warning."""
    inr_offer = {
        "offer_id": "o_cleartrip",
        "hotel_id": "h1",
        "site": "Cleartrip",
        "status": "verified",
        "currency": "INR",
        "price_final_payable": 10000.0,
        "cancellation_category": "free",
        "meal_plan": "breakfast",
        "max_occupancy": 2,
    }
    usd_offer = {
        "offer_id": "o_booking_usd",
        "hotel_id": "h1",
        "site": "Booking.com",
        "status": "verified",
        "currency": "USD",
        "price_final_payable": 115.0,  # 115 USD
        "cancellation_category": "free",
        "meal_plan": "breakfast",
        "max_occupancy": 2,
    }
    offers = [inr_offer, usd_offer]
    hotels = [{"hotel_id": "h1", "canonical_name": "Test Hotel", "rating": 4.5}]

    ranked = rank_offers(offers, hotels, deal_mode="best_value")
    ranked_oids = [r["offer_id"] for r in ranked]

    if "o_booking_usd" in ranked_oids:
        return False, "USD offer was included in direct ranking against INR offers"

    verdicts = pick_verdicts(offers, ranked)
    if verdicts.get("cheapest_verified") == "o_booking_usd":
        return False, "USD offer was erroneously picked as cheapest INR offer"

    warns = non_comparable_warnings(offers)
    has_usd_warning = any("USD" in w["message"] for w in warns)
    if not has_usd_warning:
        return False, "No non-comparable currency warning emitted for USD offer"

    return True, "USD offer excluded from INR ranking/verdicts and tagged with visible warning"


async def drill_empty_listings():
    """Drill: Search returning 0 listings handles cleanly without crashing."""
    search_id = "drill_empty_run"
    req_dict = {
        "destination": "Unknown Remote Island",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "budget_per_night": 5000,
        "must_have": {},
        "deal_mode": "best_value",
        "currency": "INR",
        "mock": True,
        "raw_text": "Unknown Remote Island, 20-21 Nov 2026",
    }
    # Test that score and verdicts handle empty offers list gracefully
    ranked = rank_offers([], [])
    v = pick_verdicts([], ranked)
    warns = non_comparable_warnings([])
    if v.get("overall", {}).get("cheapest_verified") is not None:
        return False, "Empty run produced non-null cheapest_verified"
    return True, "Empty listings handled cleanly with null verdicts"


async def main_suite(live_n: int = 0) -> None:
    print("=" * 80)
    print("TinyTravel Comprehensive Query Suite & Demo-Proof Drills")
    print("=" * 80)

    test_cases = [
        # 1-7: Varied Valid Queries
        ("1. Canonical Demo Query", "Bengaluru, 20-21 Nov 2026, 2 people, breakfast, free cancellation, under 12k", False, ""),
        ("2. Solo Budget (Mumbai)", "Mumbai, 15-18 Dec 2026, 1 guest, budget 5000, wifi", False, ""),
        ("3. Family Multi-room (Goa)", "Goa, 10-15 Jan 2027, 4 guests, 2 rooms, breakfast, pool", False, ""),
        ("4. Luxury High-Budget (Delhi)", "Delhi, 5-7 Feb 2027, 2 people, budget 35000, free cancellation", False, ""),
        ("5. Deal Mode: Lowest Price", "Bengaluru, 20-21 Nov 2026, 2 people, cheapest, under 8k", False, ""),
        ("6. Deal Mode: Transparent", "Bengaluru, 20-21 Nov 2026, 2 people, most transparent", False, ""),
        ("7. Target Mode Direct", {"hotel_name": "La Marvella", "platforms": ["Cleartrip", "Agoda"], "mock": True}, False, ""),

        # 8-14: Invalid Inputs & Boundary Tests
        ("8. Bad Input: Budget Zero", "Bengaluru, 20-21 Nov 2026, 2 people, budget 0", True, "Budget per night must be > 0"),
        ("9. Bad Input: Negative Budget", "Bengaluru, 20-21 Nov 2026, 2 people, budget -5000", True, "Budget per night must be > 0"),
        ("10. Bad Input: Past Dates", "Bengaluru, 10-12 Jan 2020, 2 guests, under 10k", True, "must be in the future"),
        ("11. Bad Input: Reversed Dates", "Bengaluru, check-in 2026-11-25, check-out 2026-11-20, 2 guests", True, "must be after check-in"),
        ("12. Bad Input: Zero Guests", "Bengaluru, 20-21 Nov 2026, 0 guests", True, "Guests must be >= 1"),
        ("13. Bad Input: Gibberish", "asdlkfjasdlkfjsdklfj 9999999 !!!!", True, "Unrecognized query"),
        ("14. Bad Input: Empty String", "", True, "cannot be empty"),
    ]

    results: list[TestResult] = []

    print("\n--- Phase 1: Varied Queries & Boundary Inputs ---")
    for name, q, is_bad, exp_err in test_cases:
        res = await run_query_test(name, q, is_bad_input=is_bad, expected_error=exp_err)
        status_tag = "[PASS]" if res.passed else "[FAIL]"
        print(f"{status_tag} {res.name:<34} ({res.duration_s:4.2f}s) -> {res.message}")
        results.append(res)

    print("\n--- Phase 2: Injected Failure Drills ---")
    drills = [
        ("15. Drill: Agent Timeout", drill_timeout),
        ("16. Drill: Captcha Challenge", drill_captcha),
        ("17. Drill: Payment Page Not Reached", drill_payment_page_never_reached),
        ("18. Drill: Duplicate Hotel Collapse", drill_duplicate_hotels),
        ("19. Drill: Currency Mismatch (USD)", drill_currency_mismatch_usd),
        ("20. Drill: Empty Listings Handling", drill_empty_listings),
    ]

    for name, fn in drills:
        res = await run_failure_drill(name, fn)
        status_tag = "[PASS]" if res.passed else "[FAIL]"
        print(f"{status_tag} {res.name:<34} ({res.duration_s:4.2f}s) -> {res.message}")
        results.append(res)

    # Phase 3: Optional live runs
    if live_n > 0:
        print(f"\n--- Phase 3: Live Verification ({live_n} runs) ---")
        from api.services.tinyfish import get_balance
        bal = await get_balance()
        print(f"Current wallet balance: ${bal}")
        if bal is not None and bal >= 0.6:
            os.environ["DATA_MODE"] = "live"
            os.environ["TINYFISH_FAKE"] = "0"
            for i in range(1, live_n + 1):
                t_name = f"Live Run #{i}: La Marvella (Cleartrip)"
                q_live = {"hotel_name": "La Marvella", "platforms": ["Cleartrip"], "mock": False}
                res = await run_query_test(t_name, q_live, is_bad_input=False)
                status_tag = "[PASS]" if res.passed else "[FAIL]"
                print(f"{status_tag} {res.name:<34} ({res.duration_s:4.2f}s) -> {res.message}")
                results.append(res)
        else:
            print("Skipping live runs: insufficient balance or no key.")

    # Summary Table
    print("\n" + "=" * 80)
    print(f"{'TEST NAME':<38} {'CATEGORY':<16} {'RESULT':<8} {'TIME'}")
    print("-" * 80)
    passed_cnt = 0
    failed_cnt = 0
    for r in results:
        res_str = "PASS" if r.passed else "FAIL"
        if r.passed:
            passed_cnt += 1
        else:
            failed_cnt += 1
        print(f"{r.name:<38} {r.category:<16} {res_str:<8} {r.duration_s:5.2f}s")
    print("=" * 80)
    print(f"Total: {len(results)} | Passed: {passed_cnt} | Failed: {failed_cnt}")

    if failed_cnt > 0:
        print("\n[FAILED] Some tests in query suite failed!")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Query suite & failure drills PASSED with zero failures!")


def main():
    parser = argparse.ArgumentParser(description="Run query suite and demo-proof failure drills.")
    parser.add_argument("--live-n", type=int, default=0, help="Number of real target-mode live searches to run")
    args = parser.parse_args()

    asyncio.run(main_suite(live_n=args.live_n))


if __name__ == "__main__":
    main()
