"""Demo-proof tests: budget endpoint, kill-switch, USD currency exclusion."""
import os
from fastapi.testclient import TestClient

from main import app
from models import BudgetInfo
from services.scoring import rank_offers, pick_verdicts, non_comparable_warnings

client = TestClient(app)


def test_budget_endpoint():
    """GET /api/budget returns wallet balance, spend so far, and spend cap."""
    resp = client.get("/api/budget")
    assert resp.status_code == 200
    data = resp.json()
    BudgetInfo.model_validate(data)
    assert "wallet_balance" in data
    assert "spend_so_far" in data
    assert "spend_cap" in data
    assert data["currency"] == "USD"
    assert data["status"] in ("ok", "capped")


def test_kill_switch_disable_live(monkeypatch):
    """DISABLE_LIVE=1 forces fake mode and activates kill switch indicator."""
    monkeypatch.setenv("DATA_MODE", "live")
    monkeypatch.setenv("DISABLE_LIVE", "1")

    # Health check shows kill_switch: true and mode: fake
    resp = client.get("/api/health")
    assert resp.status_code == 200
    h_data = resp.json()
    assert h_data["mode"] == "fake"
    assert h_data["kill_switch"] is True

    # Search in live mode with kill switch runs safely without calling TinyFish
    s_resp = client.post("/api/search", json={"text": "Bengaluru 20-21 Nov 2 guests"})
    assert s_resp.status_code == 200
    assert "search_id" in s_resp.json()


def test_usd_currency_exclusion_and_warning():
    """USD offer is excluded from INR comparison and receives visible warning."""
    offers = [
        {
            "offer_id": "inr_1",
            "hotel_id": "h1",
            "site": "Cleartrip",
            "status": "verified",
            "currency": "INR",
            "price_final_payable": 8000.0,
            "cancellation_category": "free",
        },
        {
            "offer_id": "usd_1",
            "hotel_id": "h1",
            "site": "Booking.com",
            "status": "verified",
            "currency": "USD",
            "price_final_payable": 95.0,
            "cancellation_category": "free",
        },
    ]
    hotels = [{"hotel_id": "h1", "canonical_name": "Test Hotel", "rating": 4.5}]

    # Ranking only includes INR
    ranked = rank_offers(offers, hotels)
    assert len(ranked) == 1
    assert ranked[0]["offer_id"] == "inr_1"

    # Verdicts only picks INR
    verdicts = pick_verdicts(offers, ranked)
    assert verdicts["cheapest_verified"] == "inr_1"

    # Non-comparable warnings catches USD
    warns = non_comparable_warnings(offers)
    assert any("USD" in w["message"] for w in warns)


def test_evidence_path_traversal_guards():
    """Ensure path traversal attempts (../, %2e%2e, absolute paths) return 404."""
    traversal_paths = [
        "/evidence/../.env",
        "/evidence/..%2f.env",
        "/evidence/%2e%2e/.env",
        "/evidence/%2e%2e%2f.env",
        "/evidence/C:/Windows/win.ini",
        "/evidence//etc/passwd",
        "/evidence/subdir/../../.env",
        "/evidence/..\\..\\Windows\\win.ini",
    ]
    for path in traversal_paths:
        resp = client.get(path)
        assert resp.status_code == 404, f"Path {path} should return 404 but got {resp.status_code}"


def test_recheck_max_two_per_search_guard():
    """POST /api/offers/{oid}/recheck allows max 2 per search, 3rd returns 429."""
    from main import RECHECK_SEARCH_COUNTS
    from db import save_offer

    # Set up a test offer attached to a unique search_id
    test_sid = "search_test_limit_123"
    test_oid = "off_test_limit_123"
    RECHECK_SEARCH_COUNTS.pop(test_sid, None)

    save_offer(test_oid, test_sid, {
        "offer_id": test_oid,
        "search_id": test_sid,
        "hotel_name": "Limit Hotel",
        "site": "Cleartrip",
        "status": "verified",
        "price_final_payable": 5000.0,
    })

    # 1st recheck -> ok
    r1 = client.post(f"/api/offers/{test_oid}/recheck")
    assert r1.status_code == 200

    # 2nd recheck -> ok
    r2 = client.post(f"/api/offers/{test_oid}/recheck")
    assert r2.status_code == 200

    # 3rd recheck -> 429 Too Many Requests
    r3 = client.post(f"/api/offers/{test_oid}/recheck")
    assert r3.status_code == 429
    assert "limit exceeded" in r3.json()["detail"].lower()

