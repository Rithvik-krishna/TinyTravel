import copy
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from models import ResultsResponse, SearchInput
from events import ScriptFile, EVENT_DATA_MODELS

REPO_ROOT = Path(__file__).parents[2]
demo_data = json.loads((REPO_ROOT / "fixtures" / "demo_run.json").read_text())
script_data = json.loads((REPO_ROOT / "fixtures" / "sse_script.json").read_text())


def test_demo_run_matches_results_response():
    """Validates fixtures/demo_run.json strictly matches ResultsResponse."""
    model = ResultsResponse.model_validate(demo_data)
    assert model.meta.mock is True
    assert len(model.offers) == len(demo_data["offers"])
    assert len(model.hotels) == len(demo_data["hotels"])
    assert model.verdicts.hero_hotel_id == "h1"


def test_sse_script_events_match_models():
    """Validates each event in fixtures/sse_script.json against its event model."""
    script_model = ScriptFile.model_validate(script_data)
    assert len(script_model.events) == len(script_data["events"])
    assert script_model.mock is True

    for ev in script_data["events"]:
        event_name = ev["event"]
        assert event_name in EVENT_DATA_MODELS, f"Unknown event type: {event_name}"
        data_model = EVENT_DATA_MODELS[event_name]
        validated = data_model.model_validate(ev["data"])
        assert validated is not None


def test_extra_field_in_results_fails():
    """Negative test: extra fields must fail validation (extra='forbid')."""
    bad_demo = copy.deepcopy(demo_data)
    bad_demo["unexpected_extra_field"] = "should_fail"

    with pytest.raises(ValidationError) as exc_info:
        ResultsResponse.model_validate(bad_demo)

    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" and "unexpected_extra_field" in e["loc"] for e in errors)


def test_extra_field_in_offer_fails():
    """Negative test: extra field inside a nested object must also fail."""
    bad_demo = copy.deepcopy(demo_data)
    bad_demo["offers"][0]["hallucinated_score"] = 999

    with pytest.raises(ValidationError) as exc_info:
        ResultsResponse.model_validate(bad_demo)

    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" and "hallucinated_score" in e["loc"] for e in errors)


def test_extra_field_in_sse_event_fails():
    """Negative test: extra field in SSE event data must fail."""
    bad_ev = {
        "run_id": "mock_run_h1_cleartrip",
        "step_text": "Opening search page",
        "rogue_field": "disallowed",
    }
    with pytest.raises(ValidationError) as exc_info:
        EVENT_DATA_MODELS["agent_progress"].model_validate(bad_ev)

    errors = exc_info.value.errors()
    assert any(e["type"] == "extra_forbidden" and "rogue_field" in e["loc"] for e in errors)


def test_search_input_validation():
    """Test POST /api/search input with text or structured or target mode."""
    # Free-text
    s1 = SearchInput.model_validate({"text": "Bengaluru under 10k"})
    assert s1.text == "Bengaluru under 10k"

    # Full structured
    s2 = SearchInput.model_validate(demo_data["search_request"])
    assert s2.destination == "Bengaluru"

    # Target mode
    s3 = SearchInput.model_validate({
        "hotel_name": "La Marvella",
        "platforms": ["cleartrip", "agoda", "booking"]
    })
    assert s3.hotel_name == "La Marvella"
    assert s3.platforms == ["cleartrip", "agoda", "booking"]

    # Extra field fails
    with pytest.raises(ValidationError):
        SearchInput.model_validate({"text": "test", "rogue": 123})
