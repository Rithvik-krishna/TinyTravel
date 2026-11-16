"""
Unit tests for GET /api/coverage endpoint.
"""
from fastapi.testclient import TestClient
from api.main import app
from api.models import CoverageResponse

client = TestClient(app)


def test_get_coverage_endpoint_contract():
    resp = client.get("/api/coverage")
    assert resp.status_code == 200
    data = resp.json()

    # Validate strict Pydantic model contract
    validated = CoverageResponse.model_validate(data)
    assert validated.total_sites >= 6
    assert validated.checkout_capable_sites >= 2

    # Check Cleartrip
    ct = next(s for s in validated.sites if s.site == "Cleartrip")
    assert ct.verification_level == "checkout"
    assert ct.checkout_capable is True
    assert ct.status == "verified"
    assert ct.success_rate >= 0.90

    # Check Booking.com
    bk = next(s for s in validated.sites if s.site == "Booking.com")
    assert bk.verification_level == "checkout"
    assert bk.checkout_capable is True
    assert bk.status == "verified"
    assert bk.success_rate >= 0.70
    assert bk.source_file in ["results/pass3_checkout_5hotels.json", "results/3demo_hotels_matrix_results.json"]

    # Check Agoda
    ag = next(s for s in validated.sites if s.site == "Agoda")
    assert ag.verification_level == "listing"
    assert ag.checkout_capable is False
    assert ag.listing_capable is True

    # Check Treebo
    tr = next(s for s in validated.sites if s.site == "Treebo Hotels")
    assert tr.status == "blocked"
    assert tr.blocker == "login"
