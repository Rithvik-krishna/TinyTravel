"""Contract and integration tests for DATA_MODE=saved and mock prevention."""
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from models import ResultsResponse
from events import ScriptFile

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[2]


def test_saved_fixtures_integrity():
    """Verify saved_run.json and saved_sse_script.json exist and adhere to safety invariants.
    
    A recorded run must have saved=True and mock=False with capture timestamps.
    """
    saved_run_path = ROOT / "fixtures" / "saved_run.json"
    saved_script_path = ROOT / "fixtures" / "saved_sse_script.json"

    assert saved_run_path.exists(), "fixtures/saved_run.json must exist"
    assert saved_script_path.exists(), "fixtures/saved_sse_script.json must exist"

    run_data = json.loads(saved_run_path.read_text(encoding="utf-8"))
    script_data = json.loads(saved_script_path.read_text(encoding="utf-8"))

    meta = run_data.get("_meta", {})
    # When recorded as a real saved run, saved must be True and mock must be False
    assert meta.get("saved") is True, "Recorded saved_run.json must have saved: true"
    assert meta.get("mock") is False, "Recorded saved_run.json must have mock: false"
    assert "saved_at" in meta, "Recorded saved_run.json must have saved_at timestamp"


def test_api_saved_mode_rejects_mock_data(monkeypatch):
    """Verify DATA_MODE=saved returns HTTP 503 error when files contain mock data."""
    from unittest.mock import patch
    from fastapi import HTTPException
    import main

    mock_err = HTTPException(
        status_code=503,
        detail="DATA_MODE=saved error: saved_run.json contains mock data (mock: true / saved: false); a real saved run must be recorded first."
    )
    with patch.object(main, "_get_saved_run", side_effect=mock_err), \
         patch.object(main, "_get_saved_script", side_effect=mock_err):
        monkeypatch.setenv("DATA_MODE", "saved")

        # 1. Search endpoint returns 503
        resp = client.post("/api/search", json={"text": "Bengaluru 20-21 Nov 2 guests"})
        assert resp.status_code == 503
        assert "mock data" in resp.json()["detail"].lower()

        # 2. Results endpoint returns 503
        res_resp = client.get("/api/search/any_search_id/results")
        assert res_resp.status_code == 503
        assert "mock data" in res_resp.json()["detail"].lower()


def test_api_saved_mode_serves_valid_saved_run(monkeypatch, tmp_path):
    """Verify DATA_MODE=saved serves normally when genuine saved data (mock: false, saved: true) exists."""
    saved_run_path = ROOT / "fixtures" / "saved_run.json"
    run_data = json.loads(saved_run_path.read_text(encoding="utf-8"))

    # Create genuine saved copy
    genuine_run = dict(run_data)
    genuine_run["_meta"] = dict(genuine_run["_meta"])
    genuine_run["_meta"]["mock"] = False
    genuine_run["_meta"]["saved"] = True

    from unittest.mock import patch
    with patch("main._get_saved_run", return_value=genuine_run):
        monkeypatch.setenv("DATA_MODE", "saved")

        res_resp = client.get("/api/search/test_id/results")
        assert res_resp.status_code == 200
        res_data = res_resp.json()
        assert res_data["_meta"]["saved"] is True
        assert res_data["_meta"]["mock"] is False


def test_saved_evidence_serving():
    """Verify /evidence serves artifacts saved in fixtures/evidence/."""
    fix_ev_dir = ROOT / "fixtures" / "evidence"
    fix_ev_dir.mkdir(parents=True, exist_ok=True)
    sample_file = fix_ev_dir / "sample_test_evidence.txt"
    sample_file.write_text("verifiable evidence artifact", encoding="utf-8")

    resp = client.get("/evidence/sample_test_evidence.txt")
    assert resp.status_code == 200
    assert "verifiable evidence artifact" in resp.text
