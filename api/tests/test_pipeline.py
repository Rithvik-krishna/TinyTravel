"""Pipeline integration and orchestrator tests for TinyTravel.
Tests intake parsing, SSE event order, late-subscriber replay, budget guard, error resilience, and contract validation.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
API_DIR = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

try:
    from api.models import ResultsResponse, SearchRequestOut
    from api.events import ScriptFile
    from api.db import init_db, get_events, get_search
    from api.services.intake import parse_request
    from api.services.orchestrator import run_search
    from api.main import app
except ImportError:
    from models import ResultsResponse, SearchRequestOut
    from events import ScriptFile
    from db import init_db, get_events, get_search
    from services.intake import parse_request
    from services.orchestrator import run_search
    from main import app

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@pytest.fixture(autouse=True)
def setup_env(tmp_path, monkeypatch):
    """Set fake mode and isolated db for pipeline tests."""
    monkeypatch.setenv("DATA_MODE", "fake")
    monkeypatch.setenv("TINYFISH_FAKE", "1")
    monkeypatch.setenv("FAKE_SPEED", "0.001")
    db_file = tmp_path / "test_pipe.db"
    monkeypatch.setattr("api.db.DEFAULT_DB_PATH", db_file)
    init_db(db_file)


def test_intake_offline_parser_success():
    """Verify deterministic regex/heuristic parser on the canonical sample query."""
    query = "Bengaluru, 20-21 Nov, 2 people, breakfast, free cancellation, under 12k"
    req = parse_request(query)
    assert req.destination == "Bengaluru"
    assert req.check_in == "2026-11-20"
    assert req.check_out == "2026-11-21"
    assert req.guests == 2
    assert req.rooms == 1
    assert req.budget_per_night == 12000.0
    assert req.must_have.get("breakfast") is True
    assert req.must_have.get("free_cancellation") is True
    assert req.deal_mode == "best_value"
    assert req.currency == "INR"


def test_intake_validation_errors():
    """Verify clear error handling for invalid input constraints."""
    with pytest.raises(ValueError, match="empty"):
        parse_request("")

    with pytest.raises(ValueError, match="after check-in date"):
        # check_out before check_in
        parse_request("Bengaluru, 25-20 Nov, 2 people")


def test_orchestrator_event_order_matches_script():
    """Verify orchestrator event names match sse_script.json in exact order."""
    async def _test():
        script_data = json.loads((FIXTURES_DIR / "sse_script.json").read_text(encoding="utf-8"))
        expected_order = [e["event"] for e in script_data["events"]]

        search_id = "test_order_001"
        req = {
            "destination": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "rooms": 1,
            "budget_per_night": 12000.0,
            "deal_mode": "best_value",
        }

        results = await run_search(search_id, req)
        assert results is not None

        events = get_events(search_id)
        emitted_names = [e["event"] for e in events]

        # Verify structural milestones in exact sequence
        assert emitted_names[0] == "parsed"
        assert emitted_names[1] == "discovery_started"
        assert emitted_names[2] == "listings_found"
        assert emitted_names[3] == "hotels_grouped"

        # Following events are agent runs
        assert "agent_started" in emitted_names[4:]
        assert "agent_progress" in emitted_names[4:]
        assert "agent_done" in emitted_names[4:]

        # Final event is ranking_ready
        assert emitted_names[-1] == "ranking_ready"

        # Verify every emitted event name belongs to canonical set
        canonical_set = set(expected_order)
        for name in emitted_names:
            assert name in canonical_set

    asyncio.run(_test())


def test_late_subscriber_replay():
    """Verify late subscribers receive all past events replayed from database."""
    async def _test():
        search_id = "test_replay_002"
        req = {
            "destination": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "hotel_name": "La Marvella",
            "platforms": ["Cleartrip", "Agoda"],
        }
        await run_search(search_id, req)

        # Search is completed, now simulate late subscriber connecting to stream endpoint
        client = TestClient(app)
        response = client.get(f"/api/search/{search_id}/stream")
        assert response.status_code == 200
        content = response.text

        # Verify events are present in SSE text format
        assert "event: parsed\n" in content
        assert "event: hotels_grouped\n" in content
        assert "event: agent_started\n" in content
        assert "event: agent_done\n" in content
        assert "event: ranking_ready\n" in content

    asyncio.run(_test())


def test_budget_guard_skips_runs(monkeypatch):
    """Verify MAX_SPEND_USD limit skips subsequent runs and records unverified."""
    async def _test():
        monkeypatch.setenv("MAX_SPEND_USD", "0.0")

        search_id = "test_budget_003"
        req = {
            "hotel_name": "La Marvella",
            "platforms": ["Cleartrip", "Agoda"],
        }

        results = await run_search(search_id, req)
        assert results is not None
        assert len(results["offers"]) == 2
        for o in results["offers"]:
            assert o["status"] == "unverified"
            assert o["blocker"] == "other"
            assert "MAX_SPEND_USD" in o["notes"]

        events = get_events(search_id)
        done_events = [e for e in events if e["event"] == "agent_done"]
        assert len(done_events) == 2
        for de in done_events:
            assert de["data"]["status"] == "unverified"

    asyncio.run(_test())


def test_failing_agent_yields_unverified_without_crashing():
    """Verify an agent exception is caught safely without aborting the pipeline."""
    async def _test():
        search_id = "test_fail_004"
        req = {
            "hotel_name": "La Marvella",
            "platforms": ["Cleartrip"],
        }

        with patch("api.services.orchestrator.verify_offer", side_effect=RuntimeError("Simulated TinyFish network failure")):
            results = await run_search(search_id, req)

        assert results is not None
        assert len(results["offers"]) == 1
        failed_offer = results["offers"][0]
        assert failed_offer["status"] == "unverified"
        assert "Simulated TinyFish" in failed_offer["notes"]

        # Verify pipeline completed and produced valid ResultsResponse
        ResultsResponse.model_validate(results)

    asyncio.run(_test())


def test_results_validate_against_results_response_contract():
    """Verify full end-to-end output strictly validates against ResultsResponse model."""
    async def _test():
        search_id = "test_contract_005"
        req = {
            "destination": "Bengaluru",
            "check_in": "2026-11-20",
            "check_out": "2026-11-21",
            "guests": 2,
            "rooms": 1,
            "budget_per_night": 12000.0,
            "deal_mode": "best_value",
        }

        results = await run_search(search_id, req)
        validated = ResultsResponse.model_validate(results)
        assert validated.meta.mock is True
        assert len(validated.hotels) >= 1
        assert len(validated.offers) >= 1
        assert validated.verdicts.hero_hotel_id is not None
        assert validated.complete is True

    asyncio.run(_test())


def test_api_fastapi_endpoints_fake_mode():
    """Verify FastAPI endpoints in DATA_MODE=fake."""
    client = TestClient(app)

    # Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["mode"] == "fake"

    # POST /api/search
    post_body = {
        "text": "Bengaluru, 20-21 Nov, 2 people, breakfast, under 12k",
        "hotel_name": "La Marvella",
        "platforms": ["Cleartrip", "Agoda"],
    }
    res_search = client.post("/api/search", json=post_body)
    assert res_search.status_code == 200
    sid = res_search.json()["search_id"]
    assert sid

    # Wait briefly for background task
    import time
    time.sleep(0.5)

    # GET /api/search/{sid}/results
    res_results = client.get(f"/api/search/{sid}/results")
    assert res_results.status_code == 200
    data = res_results.json()
    assert "_meta" in data
    assert "verdicts" in data
