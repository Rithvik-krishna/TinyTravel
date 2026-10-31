import asyncio
import json
from pathlib import Path
import sys
import pytest

# Ensure api directory in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.checkout import build_goal, site_url, verify_offer
from services.evidence import build_evidence
from services.scoring import (
    fee_leak_pct,
    reconciliation_status,
    reconciles,
    cancellation_category,
    determine_status,
)
from models import Offer, ProbeResult

repo_root = Path(__file__).resolve().parents[2]
demo_path = repo_root / "fixtures" / "demo_run.json"
demo_data = json.loads(demo_path.read_text(encoding="utf-8"))


# --- 1. Goal Prompt Construction Tests ---
def test_build_goal_verbatim_safety():
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "must_have": {
            "breakfast": True,
            "free_cancellation": True,
        },
    }
    goal = build_goal("La Marvella", req)

    # Invariant safety phrases must be exact
    assert 'Name "Test Guest", email "test.guest+probe@example.com", phone "9000000000"' in goal
    assert "Record the displayed total at each step in price_trail with the currency shown on screen. Do not convert currencies." in goal
    assert "Record every fee line, pre-selected add-on, and any urgency/scarcity message." in goal
    assert "STOP at the payment page. Never enter payment details, never click pay/confirm/book, never log in, never enter an OTP, never create an account." in goal
    assert "If blocked (login, OTP, captcha, empty page), stop and return the blocker." in goal
    assert "Use at most 30 steps. Return ONLY JSON in the given schema." in goal

    # Preferences & fallback
    assert "Prefer free cancellation, breakfast included" in goal
    assert "select the cheapest room that fits 2 adults, and report the actual meal plan and cancellation policy" in goal
    assert 'max_occupancy and room_type must describe the room in the final booking summary, copying the "X adults" text from that page.' in goal
    assert 'price_shown_on_listing must be the price of the same room as the final payable, or null. Never record a listing price from a different room.' in goal


# --- 2. Platform URL Tests ---
def test_site_url_confirmed_platforms():
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
    }
    # Cleartrip
    ct_url = site_url("cleartrip", req)
    assert "cleartrip.com/hotels/results?" in ct_url
    assert "city=Bengaluru" in ct_url
    assert "chk_in=2026-11-20" in ct_url
    assert "chk_out=2026-11-21" in ct_url
    assert "adults=2" in ct_url
    assert "num_rooms=1" in ct_url

    # Agoda
    agoda_url = site_url("agoda", req)
    assert "agoda.com/search?" in agoda_url
    assert "checkIn=2026-11-20" in agoda_url
    assert "checkOut=2026-11-21" in agoda_url
    assert "currency=INR" in agoda_url
    assert "adults=2" in agoda_url

    # Booking.com
    booking_url = site_url("booking", req)
    assert "booking.com/searchresults.html?" in booking_url
    assert "ss=Bengaluru" in booking_url
    assert "checkin=2026-11-20" in booking_url
    assert "checkout=2026-11-21" in booking_url
    assert "group_adults=2" in booking_url


def test_site_url_not_implemented_platforms():
    req = {"destination": "Bengaluru"}

    with pytest.raises(NotImplementedError) as exc_emt:
        site_url("easemytrip", req)
    assert "EaseMyTrip" in str(exc_emt.value)

    with pytest.raises(NotImplementedError) as exc_mmt:
        site_url("makemytrip", req)
    assert "MakeMyTrip" in str(exc_mmt.value)

    with pytest.raises(NotImplementedError) as exc_go:
        site_url("goibibo", req)
    assert "Goibibo" in str(exc_go.value)


# --- 3. Pure Function Unit Tests ---
def test_cancellation_category_classification():
    assert cancellation_category("Free cancellation until 18 Nov") == "free"
    assert cancellation_category("FREE CANCELLATION before 24h") == "free"
    assert cancellation_category("Non-refundable reservation") == "non_refundable"
    assert cancellation_category("This rate has no refund policy") == "non_refundable"
    assert cancellation_category("nonrefundable booking") == "non_refundable"
    assert cancellation_category("50% refund if cancelled 3 days prior") == "partial"
    assert cancellation_category("Cancellation fee applies") == "partial"
    assert cancellation_category("") is None
    assert cancellation_category(None) is None


def test_reconciliation_and_cleartrip_real_numbers():
    # Real Cleartrip numbers: 15639 + 1971 - 4692 - 2737 + 1095 = 11276
    fee_lines = [
        {"label": "Room price (base)", "amount": 15639.0},
        {"label": "Taxes & fees", "amount": 1971.0},
        {"label": "Discount", "amount": -4692.0},
        {"label": "Offer / coupon", "amount": -2737.0},
        {"label": "Convenience fee", "amount": 1095.0},
    ]
    final_payable = 11276.0
    listing_price = 8210.0

    assert sum(line["amount"] for line in fee_lines) == 11276.0
    assert reconciles(fee_lines, final_payable) is True
    assert reconciliation_status(fee_lines, final_payable) == "ok"

    # Fee leak % calculation
    leak = fee_leak_pct(listing_price, final_payable)
    assert leak == 37.3


def test_reconciliation_mismatch():
    mismatched_lines = [
        {"label": "Room price", "amount": 10000.0},
        {"label": "Taxes", "amount": 500.0},
    ]
    final_payable = 12000.0  # Missing 1500

    assert reconciles(mismatched_lines, final_payable) is False
    assert reconciliation_status(mismatched_lines, final_payable) == "mismatch"


def test_determine_status_rules():
    dummy_ev = [{"type": "recording", "url": "https://stream.mock", "step": "payment"}]

    # 1. Verified: all invariants satisfied
    status_v = determine_status(
        reached_payment_page=True,
        final_price=11276.0,
        evidence=dummy_ev,
        reconciliation="ok",
        blocker=None,
    )
    assert status_v == "verified"

    # 2. Blocked: blocker present
    status_b = determine_status(
        reached_payment_page=False,
        final_price=None,
        evidence=[],
        reconciliation=None,
        blocker="captcha",
    )
    assert status_b == "blocked"

    # 3. Unverified: reconciliation mismatch
    status_mismatch = determine_status(
        reached_payment_page=True,
        final_price=11276.0,
        evidence=dummy_ev,
        reconciliation="mismatch",
        blocker=None,
    )
    assert status_mismatch == "unverified"

    # 4. Unverified: missing evidence
    status_no_ev = determine_status(
        reached_payment_page=True,
        final_price=11276.0,
        evidence=[],
        reconciliation="ok",
        blocker=None,
    )
    assert status_no_ev == "unverified"

    # 5. Unverified: did not reach payment page
    status_no_pay = determine_status(
        reached_payment_page=False,
        final_price=8210.0,
        evidence=dummy_ev,
        reconciliation="ok",
        blocker=None,
    )
    assert status_no_pay == "unverified"


# --- 4. Evidence Construction Tests ---
def test_build_evidence_invariants():
    ev = build_evidence(
        streaming_url="https://agent.tinyfish.ai/live/abc",
        listing_page_text="Deluxe Double ₹8,210 per night",
        payment_page_text="Total Payable ₹11,276 includes GST and fees",
        price_shown_on_listing=8210.0,
        price_final_payable=11276.0,
        started_at="2026-10-31T12:00:00+05:30",
        finished_at="2026-10-31T12:02:30+05:30",
        currency="INR",
        mock=False,
    )
    assert len(ev) == 3

    # Recording item
    rec = next(x for x in ev if x["type"] == "recording")
    assert rec["url"] == "https://agent.tinyfish.ai/live/abc"
    assert rec["step"] == "payment"
    assert rec["extracted_value"] == 11276.0

    # Listing page text item
    txt_listing = next(x for x in ev if x["type"] == "page_text" and x["step"] == "listing")
    assert txt_listing["extracted_value"] == 8210.0

    # Payment page text item
    txt_payment = next(x for x in ev if x["type"] == "page_text" and x["step"] == "payment")
    assert txt_payment["extracted_value"] == 11276.0


# --- 5. verify_offer End-to-End Simulation Tests ---
def test_verify_offer_verified_case(monkeypatch):
    monkeypatch.setenv("TINYFISH_FAKE", "1")
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
    }

    offer = asyncio.run(verify_offer("cleartrip", "La Marvella", req))

    # Validate against executable Offer model
    validated = Offer.model_validate(offer)
    assert validated.status == "verified"
    assert validated.price_final_payable == 11276.0
    assert validated.price_shown_on_listing == 8210.0
    assert validated.fee_leak_pct == 37.3
    assert validated.reconciliation == "ok"
    assert validated.cancellation_category == "free"
    assert len(validated.evidence) > 0


def test_verify_offer_blocked_case(monkeypatch):
    monkeypatch.setenv("TINYFISH_FAKE", "1")

    # Mock agent run returning captcha blocker
    from services.tinyfish import AgentRun
    async def mock_run_agent(**kwargs):
        return AgentRun(
            run_id="run_blocked_captcha",
            status="COMPLETED",
            streaming_url="https://agent.tinyfish.ai/live/blocked",
            result={
                "site": "makemytrip",
                "reached_payment_page": False,
                "furthest_step": "listing",
                "blocker": "captcha",
                "notes": "Bot detection challenge",
            },
            started_at="2026-10-31T12:00:00+05:30",
            finished_at="2026-10-31T12:00:30+05:30",
            steps=3,
            cost_usd=0.05,
            raw={},
        )

    monkeypatch.setattr("agents.checkout.run_agent", mock_run_agent)

    req = {"destination": "Bengaluru", "url": "https://www.makemytrip.com"}
    offer = asyncio.run(verify_offer("makemytrip", "La Marvella", req))

    validated = Offer.model_validate(offer)
    assert validated.status == "blocked"
    assert validated.blocker == "captcha"
    assert validated.price_final_payable is None
    assert validated.fee_leak_pct is None


def test_verify_offer_mismatch_case(monkeypatch):
    monkeypatch.setenv("TINYFISH_FAKE", "1")

    from services.tinyfish import AgentRun
    async def mock_run_mismatch(**kwargs):
        return AgentRun(
            run_id="run_mismatch",
            status="COMPLETED",
            streaming_url="https://agent.tinyfish.ai/live/mismatch",
            result={
                "site": "cleartrip",
                "reached_payment_page": True,
                "furthest_step": "payment",
                "price_shown_on_listing": 8000.0,
                "price_final_payable": 10000.0,
                "fee_lines": [
                    {"label": "Base", "amount": 8000.0},
                    {"label": "Tax", "amount": 500.0},  # sum is 8500 != 10000
                ],
                "cancellation_policy": "Non-refundable",
                "listing_page_text": "Base: 8000",
                "payment_page_text": "Total: 10000",
            },
            started_at="2026-10-31T12:00:00+05:30",
            finished_at="2026-10-31T12:01:00+05:30",
            steps=12,
            cost_usd=0.20,
            raw={},
        )

    monkeypatch.setattr("agents.checkout.run_agent", mock_run_mismatch)

    req = {"destination": "Bengaluru"}
    offer = asyncio.run(verify_offer("cleartrip", "La Marvella", req))

    validated = Offer.model_validate(offer)
    # Reconciliation mismatch must NOT verify; status must be unverified and leak must be None
    assert validated.status == "unverified"
    assert validated.reconciliation == "mismatch"
    assert validated.fee_leak_pct is None
    assert validated.cancellation_category == "non_refundable"


def test_verify_offer_missing_evidence_case(monkeypatch):
    monkeypatch.setenv("TINYFISH_FAKE", "1")

    from services.tinyfish import AgentRun
    async def mock_run_no_evidence(**kwargs):
        return AgentRun(
            run_id="run_no_ev",
            status="COMPLETED",
            streaming_url=None,  # No recording URL
            result={
                "site": "cleartrip",
                "reached_payment_page": True,
                "furthest_step": "payment",
                "price_shown_on_listing": 8210.0,
                "price_final_payable": 11276.0,
                "fee_lines": [
                    {"label": "Room", "amount": 11276.0},
                ],
                "listing_page_text": None,
                "payment_page_text": None,
            },
            started_at="2026-10-31T12:00:00+05:30",
            finished_at="2026-10-31T12:01:00+05:30",
            steps=10,
            cost_usd=0.15,
            raw={},
        )

    monkeypatch.setattr("agents.checkout.run_agent", mock_run_no_evidence)

    req = {"destination": "Bengaluru"}
    offer = asyncio.run(verify_offer("cleartrip", "La Marvella", req))

    validated = Offer.model_validate(offer)
    assert validated.status == "unverified"
    assert len(validated.evidence) == 0


def test_occupancy_mismatch_keeps_observed_payment_page_unverified_blocker_null(monkeypatch):
    """Part a: Occupancy mismatch must NOT change reached_payment_page (kept as observed).
    Status = unverified (non-comparable), blocker = null, reason in notes.
    Blocked is only for captcha/login/otp/timeout/other that really stopped the run.
    """
    monkeypatch.setenv("TINYFISH_FAKE", "1")
    from services.tinyfish import AgentRun

    async def mock_run(**kwargs):
        return AgentRun(
            run_id="run_occ_obs",
            status="completed",
            streaming_url="https://agent.tinyfish.ai/live/occ_obs",
            result={
                "site": "agoda",
                "reached_payment_page": True,
                "furthest_step": "payment",
                "blocker": "other",  # Raw TinyFish may return other, but run was NOT stopped
                "hotel_name": "La Marvella",
                "room_type": "Executive Twin",
                "max_occupancy": 1,  # Fits 1 adult, search asked for 2
                "meal_plan": "Breakfast included",
                "cancellation_policy": "Free cancellation",
                "price_shown_on_listing": 12000.0,
                "price_final_payable": 15000.0,
                "fee_lines": [
                    {"label": "Room", "amount": 15000.0},
                ],
                "listing_page_text": "Listing text",
                "payment_page_text": "Payment text",
            },
            started_at="2026-10-31T12:00:00+05:30",
            finished_at="2026-10-31T12:01:00+05:30",
            steps=15,
            cost_usd=0.20,
            raw={},
        )

    monkeypatch.setattr("agents.checkout.run_agent", mock_run)

    req = {"guests": 2, "destination": "Bengaluru"}
    offer = asyncio.run(verify_offer("agoda", "La Marvella", req))

    # Keep reached_payment_page as observed (True)
    assert offer["reached_payment_page"] is True
    # Status = unverified (non-comparable)
    assert offer["status"] == "unverified"
    # Blocker = null (not stopped by platform blocker)
    assert offer["blocker"] is None
    # Reason in notes
    assert "Occupancy mismatch: room fits 1 adults but search requested 2" in offer["notes"]
    # Fee leak pct is None for non-comparable / unverified
    assert offer["fee_leak_pct"] is None

    # Contract model validates cleanly
    validated = Offer.model_validate(offer)
    assert validated.status == "unverified"
    assert validated.blocker is None
    assert validated.reached_payment_page is True


def test_fee_leak_pct_same_room_rule():
    """Part c: price_shown_on_listing must be the price of the same room as the final payable, or null.
    Never compute fee_leak_pct from a different room.
    """
    # Same room normal calculation
    assert fee_leak_pct(1000.0, 1200.0, same_room=True) == 20.0

    # If price_shown_on_listing is null / None -> leak is None
    assert fee_leak_pct(None, 1200.0) is None

    # If same_room is False -> leak is None (never compute fee_leak_pct from a different room)
    assert fee_leak_pct(1000.0, 1200.0, same_room=False) is None

    # Status determine_status handles occupancy_mismatch explicitly
    assert determine_status(
        reached_payment_page=True,
        final_price=1200.0,
        evidence=[{"type": "recording"}],
        reconciliation="ok",
        blocker=None,
        occupancy_mismatch=True,
    ) == "unverified"

    # Status determine_status without mismatch verifies
    assert determine_status(
        reached_payment_page=True,
        final_price=1200.0,
        evidence=[{"type": "recording"}],
        reconciliation="ok",
        blocker=None,
        occupancy_mismatch=False,
    ) == "verified"

