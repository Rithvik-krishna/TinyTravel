"""Tests for final P0 backend features:
- GET /api/history
- GET /api/search/{id}/report
- GET /api/offers/{id}/report-fee-draft
- GET /api/fee-glossary
- Fee line classification on all fixture fee labels
- Live summary_strip in partial results
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

api_dir = Path(__file__).resolve().parent.parent
root_dir = api_dir.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from api.main import app
    from api.services.fees import classify_fee_label, FEE_GLOSSARY
    from api.services.reporting import generate_html_report, generate_fee_draft, SAFETY_STATEMENT
    from api.db import save_price_history, get_price_history
except ImportError:
    from main import app
    from services.fees import classify_fee_label, FEE_GLOSSARY
    from services.reporting import generate_html_report, generate_fee_draft, SAFETY_STATEMENT
    from db import save_price_history, get_price_history


@pytest.fixture
def client():
    return TestClient(app)


def test_fee_glossary_endpoint(client):
    """GET /api/fee-glossary returns static JSON with required categories."""
    resp = client.get("/api/fee-glossary")
    assert resp.status_code == 200
    glossary = resp.json()

    # Must contain common fee line explanations
    assert "gst_taxes" in glossary
    assert "convenience_fee" in glossary
    assert "platform_service_fee" in glossary
    assert "payment_gateway_fee" in glossary
    assert "resort_property_fee" in glossary
    assert "trip_protection_addon" in glossary

    # Must include valid kind values
    valid_kinds = {"tax", "platform_fee", "property_fee", "add_on", "other"}
    for k, item in glossary.items():
        assert item["kind"] in valid_kinds
        assert len(item["description"]) > 20
        # Explanations must be general and cautious
        desc = item["description"].lower()
        assert any(c in desc for c in ["typically", "may", "imposed by", "charged by", "statutory"])


def test_classify_fee_labels_all_fixtures():
    """Verify fee classification on all known fixture fee labels."""
    test_cases = [
        # Taxes
        ("Taxes & fees", "tax"),
        ("Taxes & charges", "tax"),
        ("Taxes & service fees", "tax"),
        ("Hotel taxes", "tax"),
        ("GST / Government taxes", "tax"),
        # Platform fees
        ("Convenience fee", "platform_fee"),
        ("Platform fee", "platform_fee"),
        ("Booking fee", "platform_fee"),
        ("Payment gateway fee", "platform_fee"),
        # Property fees
        ("Resort fee", "property_fee"),
        ("Facility fee", "property_fee"),
        ("Amenity fee", "property_fee"),
        # Add-ons
        ("Trip protection", "add_on"),
        ("Travel insurance", "add_on"),
        ("Flexible cancellation pass", "add_on"),
        ("Covid assistance addon", "add_on"),
        # Other: base rates, discounts, coupons, unknown
        ("Room price (base)", "other"),
        ("Room price", "other"),
        ("1 room x 1 night", "other"),
        ("Discount", "other"),
        ("Property discount", "other"),
        ("Offer / coupon", "other"),
        ("Coupon discount (CTHOTEL)", "other"),
        ("Mysterious miscellaneous surcharge", "other"),
        ("", "other"),
    ]

    for label, expected_kind in test_cases:
        kind = classify_fee_label(label)
        assert kind == expected_kind, f"Failed on label '{label}': got '{kind}', expected '{expected_kind}'"


def test_history_endpoint(client):
    """GET /api/history returns rows ordered newest first.
    No real data -> empty list. Mock/fake observations excluded by default.
    """
    import uuid
    hotel_name = f"Isolated Hotel {uuid.uuid4().hex[:8]}"
    platform = "Cleartrip"

    # 1. No real data -> empty list
    resp = client.get(f"/api/history?hotel={hotel_name}")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Insert mock observation (mock=True)
    save_price_history(
        hotel=hotel_name,
        platform=platform,
        amount=9500.0,
        captured_at="2026-10-31T12:00:00+05:30",
        offer_id="off_mock_1",
        run_id="run_mock_1",
        mock=True,
    )

    # By default, mock observation is excluded -> returns empty list
    resp_default = client.get(f"/api/history?hotel={hotel_name}")
    assert resp_default.status_code == 200
    assert resp_default.json() == []

    # With include_mock=true -> returns mock observation with mock: true
    resp_mock = client.get(f"/api/history?hotel={hotel_name}&include_mock=true")
    assert resp_mock.status_code == 200
    mock_rows = resp_mock.json()
    assert len(mock_rows) == 1
    assert mock_rows[0]["mock"] is True
    assert mock_rows[0]["amount"] == 9500.0

    # 3. Insert real recorded observation (mock=False)
    save_price_history(
        hotel=hotel_name,
        platform=platform,
        amount=10250.0,
        captured_at="2026-10-31T13:00:00+05:30",
        offer_id="off_real_1",
        run_id="run_real_1",
        mock=False,
    )

    # Real observation returned without include_mock
    resp_real = client.get(f"/api/history?hotel={hotel_name}")
    assert resp_real.status_code == 200
    real_rows = resp_real.json()
    assert len(real_rows) == 1
    assert real_rows[0]["amount"] == 10250.0
    assert real_rows[0]["mock"] is False
    assert real_rows[0]["offer_id"] == "off_real_1"


def test_search_report_html_endpoint(client):
    """GET /api/search/{id}/report returns self-contained printable HTML evidence report."""
    resp = client.get("/api/search/demo/report")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html_text = resp.text

    # Must contain safety statement verbatim
    assert SAFETY_STATEMENT in html_text
    # Must contain factual observation phrasing
    assert "Observed on this run" in html_text or "Observed On This Run" in html_text
    # Must contain printable CSS styling
    assert "@media print" in html_text
    # Must not contain external script tags or external CSS CDN links
    assert "<script src=" not in html_text
    assert "https://cdn." not in html_text
    assert "https://fonts.googleapis.com" not in html_text

    # 404 for unknown search id
    resp_404 = client.get("/api/search/unknown_sid_xyz/report")
    assert resp_404.status_code == 404


def test_reporting_html_escapes_xss():
    """Verify html.escape strictly sanitizes dynamic hotel names, labels, URLs, notes, and page text."""
    xss_payload = "<script>alert(1)</script>"
    xss_note = "<img src=x onerror=alert(2)>"
    xss_page_text = "<svg onload=alert(3)>"
    xss_url = "https://example.com/hotel?id=1&name=<script>alert(4)</script>"

    results = {
        "search_request": {
            "destination": f"Bengaluru {xss_payload}",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "rooms": 1,
        },
        "verdicts": {
            "overall": {"headlines": {"cheapest_verified": f"Hotel {xss_payload}"}}
        },
        "summary_strip": {"listings_found": 1, "unique_hotels": 1, "verified": 1},
        "offers": [
            {
                "offer_id": "off_xss_1",
                "hotel_name": f"Luxury Palace {xss_payload}",
                "site": f"Cleartrip {xss_payload}",
                "status": "verified",
                "reconciliation": "ok",
                "notes": xss_note,
                "listing_page_text": xss_page_text,
                "hotel_url": xss_url,
                "price_shown_on_listing": 5000.0,
                "price_final_payable": 6500.0,
                "fee_lines": [
                    {"label": f"Convenience Fee {xss_payload}", "amount": 500.0, "fee_kind": "platform_fee"}
                ],
                "evidence": [
                    {"step": "payment", "type": "screenshot", "url": xss_url}
                ]
            }
        ]
    }

    report = generate_html_report(results, search_id=f"sid_{xss_payload}")

    # Raw script and dangerous tags must NOT be present
    assert "<script>alert(1)</script>" not in report
    assert "<img src=x onerror=alert(2)>" not in report
    assert "<svg onload=alert(3)>" not in report
    assert "<script>alert(4)</script>" not in report

    # Escaped versions must be present
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in report
    assert "&lt;img src=x onerror=alert(2)&gt;" in report
    assert "&lt;svg onload=alert(3)&gt;" in report


def test_report_fee_draft_endpoint(client):
    """GET /api/offers/{id}/report-fee-draft returns polite, factual draft citing fees and excluding taxes."""
    resp = client.get("/api/offers/h1_cleartrip/report-fee-draft")
    assert resp.status_code == 200
    draft = resp.json()

    assert draft["offer_id"] == "h1_cleartrip"
    assert "Cleartrip" in draft["platform"]
    assert "La Marvella" in draft["hotel_name"]
    assert "subject" in draft
    assert "draft_message" in draft
    assert draft["observed_leak_pct"] == 37.3
    assert draft["currency"] == "INR"

    msg = draft["draft_message"]
    # Polite and factual
    assert "Dear Cleartrip Support Team" in msg
    assert "inquire" in msg or "clarification" in msg
    assert "Observed Details" in msg

    # Only cites platform_fee / property_fee / add_on (Convenience fee: INR 1,095.00)
    assert "Convenience fee: INR 1,095.00" in msg
    # Excludes taxes from fees
    assert "Taxes & fees" not in msg
    # Excludes room price base and discount lines from fees
    assert "Room price (base)" not in msg
    assert "Discount" not in msg

    # Never accuse or claim dishonesty
    assert "cheat" not in msg.lower()
    assert "fraud" not in msg.lower()
    assert "dishonest" not in msg.lower()
    assert "scam" not in msg.lower()

    # 404 for unknown offer
    resp_404 = client.get("/api/offers/unknown_offer_xyz/report-fee-draft")
    assert resp_404.status_code == 404


def test_summary_strip_partial_results(monkeypatch):
    """Verify summary_strip updates live during search execution."""
    import asyncio
    monkeypatch.setenv("DATA_MODE", "fake")
    monkeypatch.setenv("TINYFISH_FAKE", "1")

    try:
        from api.services.orchestrator import run_search, get_search_results
    except ImportError:
        from services.orchestrator import run_search, get_search_results

    sid = "test_summary_partial_run"
    req_payload = {
        "destination": "Bengaluru",
        "check_in": "2026-11-20",
        "check_out": "2026-11-21",
        "guests": 2,
        "rooms": 1,
        "budget_per_night": 12000,
    }

    results = asyncio.run(run_search(sid, req_payload))
    strip = results.get("summary_strip", {})

    assert strip["listings_found"] > 0
    assert strip["unique_hotels"] > 0
    assert strip["verified"] >= 1
    assert strip["avg_fee_leak_pct"] is not None
