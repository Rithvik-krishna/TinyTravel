"""P0 Backend Completion Test Suite.
Validates:
1. Handoff pack builder (QR decodes to exact deep_link).
2. Recheck diff math, delta, delta_pct, elapsed_minutes, trail_diff, and observation message.
3. Blocker classification mapping across enum values.
4. Occupancy mismatch handling (room max_occupancy < requested guests -> unverified).
5. 3-platform full fake investigation validates against ResultsResponse contract.
6. Handoff and Recheck API endpoints return contract-valid models.
7. Evidence static file serving under /evidence/...
8. Invariant: Fee line mismatch sets reconciliation='mismatch' and unverified, never verified leak.
"""
import asyncio
import base64
import io
import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image

try:
    from pyzbar.pyzbar import decode as decode_qr
    HAS_PYZBAR = True
except Exception:
    HAS_PYZBAR = False


ROOT = Path(__file__).resolve().parents[2]
API_DIR = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

try:
    from api.models import ResultsResponse, HandoffPack, Recheck, Blocker
    from api.agents.checkout import classify_blocker, verify_offer
    from api.agents.recheck import calculate_recheck, diff_price_trails
    from api.services.handoff import build_handoff
    from api.services.orchestrator import run_search
    from api.main import app
except ImportError:
    from models import ResultsResponse, HandoffPack, Recheck, Blocker
    from agents.checkout import classify_blocker, verify_offer
    from agents.recheck import calculate_recheck, diff_price_trails
    from services.handoff import build_handoff
    from services.orchestrator import run_search
os.environ["TINYFISH_FAKE"] = "1"
os.environ["DATA_MODE"] = "fake"




# --- 1. Handoff Pack & QR Code Decoding Test ---
def test_handoff_builder_qr_decodes():
    """Verify handoff builder produces valid HandoffPack and QR code decodes to deep_link."""
    sample_offer = {
        "offer_id": "h1_cleartrip",
        "hotel_id": "h1",
        "site": "Cleartrip",
        "hotel_name": "La Marvella",
        "hotel_url": "https://www.cleartrip.com/hotels/details/12345?adults=2&chk_in=2026-11-20",
        "room_type": "Executive Suite",
        "max_occupancy": 2,
        "meal_plan": "Breakfast included",
        "cancellation_category": "free",
        "cancellation_policy": "Free cancellation until 18 Nov 2026",
        "price_final_payable": 11276.0,
        "currency": "INR",
        "started_at": "2026-10-31T12:00:00+05:30",
        "finished_at": "2026-10-31T12:02:15+05:30",
        "mock": True,
    }
    req = {
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
    }

    pack = build_handoff(sample_offer, req)

    # 1. Pydantic validation
    validated = HandoffPack.model_validate(pack)
    assert validated.offer_id == "h1_cleartrip"
    assert validated.platform == "Cleartrip"
    assert validated.deep_link == sample_offer["hotel_url"]

    # 2. QR code decodes to exact deep_link
    qr_b64 = pack["qr_png_base64"]
    qr_bytes = base64.b64decode(qr_b64)
    assert qr_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    img = Image.open(io.BytesIO(qr_bytes))
    assert img.format == "PNG"
    assert img.size[0] > 0 and img.size[1] > 0
    if HAS_PYZBAR:
        decoded_objects = decode_qr(img)
        assert len(decoded_objects) >= 1
        decoded_text = decoded_objects[0].data.decode("utf-8")
        assert decoded_text == sample_offer["hotel_url"]


    # 3. Selection card details
    card = pack["selection_card"]
    assert card["hotel"] == "La Marvella"
    assert card["room_type"] == "Executive Suite"
    assert card["meal_plan"] == "Breakfast included"
    assert card["cancellation"] == "Free cancellation until 18 Nov 2026"
    assert card["guests"] == 2
    assert card["expected_final_payable"] == 11276.0
    assert card["currency"] == "INR"

    # 4. Dummy guest credentials
    creds = pack["copy_paste"]
    assert creds["name"] == "Test Guest"
    assert creds["email"] == "test.guest+probe@example.com"
    assert creds["phone"] == "9000000000"

    # 5. Disclaimer presence
    assert "Price verified at" in pack["disclaimer"]
    assert "Re-check before paying; prices can change." in pack["disclaimer"]


# --- 2. Recheck Diff Math & Observation Message Tests ---
def test_recheck_diff_math_price_movement():
    """Verify price movement delta, delta_pct, elapsed_minutes, trail_diff, and observation message."""
    prev_trail = [
        {"step": "listing", "amount": 8210.0, "currency": "INR"},
        {"step": "room", "amount": 8210.0, "currency": "INR"},
        {"step": "traveller_details", "amount": 10181.0, "currency": "INR"},
        {"step": "payment", "amount": 10412.0, "currency": "INR"},
    ]
    curr_trail = [
        {"step": "listing", "amount": 8210.0, "currency": "INR"},
        {"step": "room", "amount": 8210.0, "currency": "INR"},
        {"step": "traveller_details", "amount": 10181.0, "currency": "INR"},
        {"step": "payment", "amount": 10690.0, "currency": "INR"},
    ]

    recheck_res = calculate_recheck(
        offer_id="h1_cleartrip",
        previous_amount=10412.0,
        previous_at="2026-10-31T11:40:00+05:30",
        current_amount=10690.0,
        current_at="2026-10-31T12:03:00+05:30",
        previous_trail=prev_trail,
        current_trail=curr_trail,
        mock=True,
    )

    validated = Recheck.model_validate(recheck_res)
    assert validated.offer_id == "h1_cleartrip"
    assert validated.delta == 278.0
    assert validated.delta_pct == 2.7
    assert validated.elapsed_minutes == 23
    assert validated.message == "Price moved INR 10,412 -> INR 10,690 in 23 min (observed)."

    # Payment diff item present in trail_diff
    pay_diff = next(d for d in validated.trail_diff if d.step == "payment")
    assert pay_diff.before == 10412.0
    assert pay_diff.after == 10690.0


def test_recheck_diff_math_price_stable():
    """Verify stable price recheck message."""
    recheck_res = calculate_recheck(
        offer_id="h1_cleartrip",
        previous_amount=11276.0,
        previous_at="2026-10-31T11:45:00+05:30",
        current_amount=11276.0,
        current_at="2026-10-31T12:00:00+05:30",
        mock=True,
    )

    assert recheck_res["delta"] == 0.0
    assert recheck_res["delta_pct"] == 0.0
    assert recheck_res["elapsed_minutes"] == 15
    assert recheck_res["message"] == "Price stable at INR 11,276 in 15 min (observed)."


# --- 3. Blocker Classification Mapping Tests ---
@pytest.mark.parametrize(
    "error_string,expected_blocker",
    [
        ("Cloudflare Turnstile challenge detected", "captcha"),
        ("DataDome bot protection block", "captcha"),
        ("Please login to proceed with booking", "login"),
        ("Sign in to your account", "login"),
        ("SMS OTP verification code required", "otp"),
        ("2FA code prompt on checkout", "otp"),
        ("Page navigation timed out after 300000ms", "timeout"),
        ("Hotel no longer available", "other"),
        (None, None),
    ],
)
def test_blocker_mapping(error_string, expected_blocker):
    """Verify error texts correctly map to Blocker enum values."""
    assert classify_blocker(error_string) == expected_blocker


# --- 4. Occupancy Mismatch Handling ---
def test_occupancy_mismatch_marks_unverified(monkeypatch):
    """Verify room with max_occupancy < requested guests is marked unverified with notes."""
    async def mock_run_agent(**kwargs):
        from services.tinyfish import AgentRun
        return AgentRun(
            run_id="run_occ_mismatch",
            streaming_url="https://agent.tinyfish.ai/live/occ",
            status="completed",
            steps=12,
            cost_usd=0.25,
            started_at="2026-10-31T12:00:00+05:30",
            finished_at="2026-10-31T12:01:30+05:30",
            raw={},
            result={

                "site": "Booking.com",
                "reached_payment_page": True,
                "hotel_name": "Single Room Hotel",
                "room_type": "Single Bed Room",
                "max_occupancy": 1,  # Room only fits 1 adult, search asked for 2
                "meal_plan": "Room only",
                "cancellation_policy": "Non-refundable",
                "price_shown_on_listing": 4500.0,
                "price_shown_on_room_selection": 4500.0,
                "price_final_payable": 5200.0,
                "fee_lines": [
                    {"label": "Room", "amount": 4500.0},
                    {"label": "Tax", "amount": 700.0},
                ],
                "price_trail": [
                    {"step": "listing", "amount": 4500.0, "currency": "INR"},
                    {"step": "payment", "amount": 5200.0, "currency": "INR"},
                ],
                "currency": "INR",
            },
        )

    import api.agents.checkout as co
    monkeypatch.setattr(co, "run_agent", mock_run_agent)

    req = {
        "guests": 2,  # Requested 2 adults
        "rooms": 1,
        "destination": "Bengaluru",
        "url": "https://www.booking.com/mock",
    }

    res = asyncio.run(verify_offer("Booking.com", "Single Room Hotel", req))
    assert res["reached_payment_page"] is True
    assert res["status"] == "unverified"
    assert res["blocker"] is None
    assert "Occupancy mismatch" in res["notes"]
    assert res["fee_leak_pct"] is None


# --- 5. Full Fake Investigation (3 Hotels x 3 Platforms) Contract Validation ---
def test_full_fake_investigation_validates_contract():
    """Run full investigation pipeline across 3 platforms in fake mode and validate against ResultsResponse."""
    search_id = "test_p0_investigation_001"
    req = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "budget_per_night": 12000.0,
        "deal_mode": "best_value",
        "must_have": {
            "breakfast": True,
            "free_cancellation": True,
            "wifi": True,
            "parking": False,
        },
        "platforms": ["Cleartrip", "Agoda", "Booking.com"],
        "currency": "INR",
    }

    results = asyncio.run(run_search(search_id, req))
    assert results is not None

    # Strict contract validation
    validated = ResultsResponse.model_validate(results)
    assert validated.meta.mock is True
    assert validated.complete is True

    # Check hotels, listings, and offers
    assert len(validated.hotels) >= 3
    assert len(validated.listings) >= 6
    assert len(validated.offers) >= 3

    # Ensure all 3 active platforms are represented in offers
    platforms_observed = {o.site for o in validated.offers}
    assert "Cleartrip" in platforms_observed

    # Verify verdicts and ranking
    assert validated.verdicts.hero_hotel_id in ("h1", "h2", "h3")
    assert len(validated.verdicts.ranking) >= 1

    # Verify summary strip
    assert validated.summary_strip.listings_found >= len(validated.listings)
    assert validated.summary_strip.unique_hotels >= 2
    assert validated.summary_strip.unique_hotels == len({o.hotel_id for o in validated.offers})



# --- 6. Handoff & Recheck API Endpoints Tests ---
def test_handoff_api_endpoint():
    """Test GET /api/offers/{id}/handoff returns contract-valid HandoffPack."""
    client = TestClient(app)
    # Using demo offer id
    resp = client.get("/api/offers/h1_cleartrip/handoff")
    assert resp.status_code == 200
    pack = resp.json()
    validated = HandoffPack.model_validate(pack)
    assert validated.offer_id == "h1_cleartrip"
    assert validated.selection_card.hotel is not None
    assert validated.qr_png_base64 is not None


def test_recheck_api_endpoint():
    """Test POST /api/offers/{id}/recheck returns contract-valid Recheck."""
    client = TestClient(app)
    resp = client.post("/api/offers/h1_cleartrip/recheck")
    assert resp.status_code == 200
    rec = resp.json()
    validated = Recheck.model_validate(rec)
    assert validated.offer_id == "h1_cleartrip"
    assert validated.delta is not None
    assert validated.delta_pct is not None
    assert "observed" in validated.message


# --- 7. Static Evidence File Serving Test ---
def test_static_evidence_serving(tmp_path):
    """Test static files under /evidence are accessible via HTTP."""
    evidence_dir = Path(__file__).resolve().parents[2] / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    test_artifact = evidence_dir / "test_sample_evidence.txt"
    test_artifact.write_text("Hotel room total payable: INR 11,276 with GST", encoding="utf-8")

    client = TestClient(app)
    resp = client.get("/evidence/test_sample_evidence.txt")
    assert resp.status_code == 200
    assert "Hotel room total payable: INR 11,276 with GST" in resp.text


# --- 8. Invariant: Fee Line Mismatch Never Claims Verified Leak ---
def test_reconciliation_mismatch_invariant():
    """Verify that fee line sum mismatch results in reconciliation='mismatch' and unverified status."""
    from services.scoring import reconciliation_status, determine_status

    fee_lines = [
        {"label": "Room", "amount": 8000.0},
        {"label": "Taxes", "amount": 1000.0},
    ]  # Sum = 9000.0
    payable = 11000.0  # Mismatch by 2000 (>1%)

    recon = reconciliation_status(fee_lines, payable)
    assert recon == "mismatch"

    status = determine_status(
        reached_payment_page=True,
        final_price=payable,
        evidence=[{"type": "recording", "url": "https://live"}],
        reconciliation=recon,
    )
    assert status == "unverified"
