"""
Unit and Integration Tests for Agent Router, Playbooks, Evidence, and Safety Invariants.
"""
import asyncio
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock

from models import ProbeResult, Offer
from services.agent_router import run_hybrid_agent, run_own_playbook
from services.evidence import build_evidence
from agents.playbooks.cleartrip import to_probe_result_dict as ct_to_probe
from agents.playbooks.agoda import to_probe_result_dict as agoda_to_probe
from agents.checkout import verify_offer


def test_probe_result_schema_conformance():
    """Verify that playbook raw output when filtered via to_probe_result_dict passes ProbeResult validation."""
    sample_ct_output = {
        "site": "Cleartrip",
        "reached_payment_page": True,
        "furthest_step": "payment",
        "blocker": None,
        "hotel_name": "Radisson Blu Atria Bengaluru",
        "hotel_url": "https://www.cleartrip.com/hotels/details/radisson-blu-atria-bengaluru-2043762",
        "room_type": "Superior Room",
        "max_occupancy": 2,
        "meal_plan": "Room Only",
        "cancellation_policy": "Free cancellation",
        "price_shown_on_listing": 9387.0,
        "price_shown_on_room_selection": 9387.0,
        "price_final_payable": 11077.0,
        "fee_lines": [
            {"label": "Base Price", "amount": 9387.0, "fee_kind": "property_fee"},
            {"label": "Taxes & Fees", "amount": 1690.0, "fee_kind": "tax"},
        ],
        "preselected_addons": [],
        "urgency_or_scarcity_messages": [],
        "price_trail": [
            {"step": "room", "amount": 9387.0, "currency": "INR"},
            {"step": "payment", "amount": 11077.0, "currency": "INR"},
        ],
        "currency": "INR",
        "notes": "Deterministic playbook completed.",
        "listing_page_text": "Radisson Blu Atria Bengaluru - INR 9,387",
        "payment_page_text": "Base: INR 9,387. Taxes: INR 1,690. Total: INR 11,077",
        "rate_cohort": "cheapest_free_cancellation",
        "cheapest_any_payable": 10611.0,
        "pay_now": 11077.0,
        "pay_at_hotel": 0.0,
        # Operational fields that must be filtered out for ProbeResult
        "steps": 7,
        "seconds": 21.8,
        "cost_usd": 0.0,
        "status": "verified",
    }

    filtered = ct_to_probe(sample_ct_output)
    probe = ProbeResult.model_validate(filtered)
    assert probe.site == "Cleartrip"
    assert probe.reached_payment_page is True
    assert probe.price_final_payable == 11077.0
    assert probe.rate_cohort == "cheapest_free_cancellation"


def test_evidence_builder_screenshots_and_text(tmp_path, monkeypatch):
    """Verify build_evidence captures screenshots and page text without fabricating URLs."""
    req_offer_id = "test_off_12345"
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir(parents=True)
    
    # Mock evidence path to temp dir
    fake_screenshot = ev_dir / f"{req_offer_id}_screenshot.png"
    fake_screenshot.write_bytes(b"PNGDATA")

    items = build_evidence(
        streaming_url=None,
        listing_page_text="Listing excerpt for hotel",
        payment_page_text="Payable amount: INR 11,077",
        price_shown_on_listing=9387.0,
        price_final_payable=11077.0,
        started_at="2026-11-20T10:00:00+05:30",
        finished_at="2026-11-20T10:00:25+05:30",
        currency="INR",
        mock=False,
        offer_id=req_offer_id,
        screenshot_url=f"/evidence/{req_offer_id}_screenshot.png",
    )

    types = [item["type"] for item in items]
    assert "screenshot" in types
    assert "page_text" in types
    
    screenshot_item = next(it for it in items if it["type"] == "screenshot")
    assert screenshot_item["url"] == f"/evidence/{req_offer_id}_screenshot.png"
    assert screenshot_item["extracted_value"] == 11077.0


def test_agent_router_own_routing(monkeypatch):
    """Verify AGENT_RUNNER=own routes to own playbook and produces valid Offer schema."""
    async def _run():
        monkeypatch.setenv("AGENT_RUNNER", "own")

        mock_playbook_output = {
            "site": "Cleartrip",
            "reached_payment_page": True,
            "furthest_step": "payment",
            "blocker": None,
            "hotel_name": "Radisson Blu Atria Bengaluru",
            "hotel_url": "https://www.cleartrip.com/hotels/details/2043762",
            "room_type": "Superior Room",
            "max_occupancy": 2,
            "meal_plan": "Room Only",
            "cancellation_policy": "Free cancellation",
            "price_shown_on_listing": 9387.0,
            "price_shown_on_room_selection": 9387.0,
            "price_final_payable": 11077.0,
            "fee_lines": [
                {"label": "Base Price", "amount": 9387.0, "fee_kind": "property_fee"},
                {"label": "Taxes & Fees", "amount": 1690.0, "fee_kind": "tax"},
            ],
            "preselected_addons": [],
            "urgency_or_scarcity_messages": [],
            "price_trail": [
                {"step": "room", "amount": 9387.0, "currency": "INR"},
                {"step": "payment", "amount": 11077.0, "currency": "INR"},
            ],
            "currency": "INR",
            "notes": "Verified via own playbook mock",
            "listing_page_text": "Radisson Blu Atria",
            "payment_page_text": "Payable: 11077",
            "rate_cohort": "cheapest_free_cancellation",
            "cheapest_any_payable": 10611.0,
            "pay_now": 11077.0,
            "pay_at_hotel": 0.0,
            "steps": 7,
            "seconds": 21.5,
        }

        with patch("api.agents.playbooks.cleartrip.run_cleartrip_playbook", new=AsyncMock(return_value=mock_playbook_output)):
            req = {"destination": "Bengaluru", "guests": 2, "check_in": "2026-11-20", "check_out": "2026-11-21"}
            res = await verify_offer("cleartrip", "Radisson Blu Atria Bengaluru", req)

            assert res["status"] == "verified"
            assert res["reconciliation"] == "ok"
            assert res["price_final_payable"] == 11077.0
            assert res["cost_usd"] == 0.0
            assert res["steps"] == 7

            # Validate with strict Offer schema
            offer = Offer.model_validate(res)
            assert offer.site == "Cleartrip"
            assert offer.status == "verified"

    asyncio.run(_run())


def test_agent_router_tinyfish_routing(monkeypatch):
    """Verify AGENT_RUNNER=tinyfish routes to TinyFish agent."""
    async def _run():
        monkeypatch.setenv("AGENT_RUNNER", "tinyfish")
        monkeypatch.setenv("TINYFISH_FAKE", "1")

        req = {"destination": "Bengaluru", "guests": 2, "check_in": "2026-11-20", "check_out": "2026-11-21"}
        res = await run_hybrid_agent("cleartrip", "Radisson Blu Atria Bengaluru", req, runner="tinyfish")

        assert res["status"] in ("verified", "unverified", "blocked")
        assert res["mock"] is True

    asyncio.run(_run())
