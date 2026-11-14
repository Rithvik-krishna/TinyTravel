"""
Unit tests for Gemini intake integration and provider switching.
"""
import json
from unittest.mock import patch, MagicMock
import pytest

from api.services.intake import parse_request, parse_request_gemini


def test_parse_request_gemini_mock():
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "destination": "Bengaluru",
                                "area_hint": "Koramangala",
                                "check_in": "2026-11-20",
                                "check_out": "2026-11-21",
                                "guests": 2,
                                "rooms": 1,
                                "budget_per_night": 7500.0,
                                "must_have": {
                                    "breakfast": True,
                                    "free_cancellation": True,
                                    "parking": False,
                                    "wifi": True,
                                },
                                "deal_mode": "best_value",
                                "currency": "INR",
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = parse_request_gemini("hotels in Koramangala under 7500 with breakfast", api_key="dummy_key")
        assert res["destination"] == "Bengaluru"
        assert res["area_hint"] == "Koramangala"
        assert res["budget_per_night"] == 7500.0
        assert res["must_have"]["breakfast"] is True


def test_parse_request_provider_env_flag(monkeypatch):
    # Test INTAKE_PROVIDER=heuristic forces deterministic regex
    monkeypatch.setenv("INTAKE_PROVIDER", "heuristic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    req = parse_request("Hotel in Bengaluru from 20 to 21 Nov 2026 for 2 guests")
    assert req.destination == "Bengaluru"
    assert req.check_in == "2026-11-20"
    assert req.check_out == "2026-11-21"
    assert req.guests == 2


def test_parse_request_gemini_fallback_on_error(monkeypatch):
    monkeypatch.setenv("INTAKE_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")

    with patch("urllib.request.urlopen", side_effect=Exception("API connection timeout")):
        # Should fall back cleanly to heuristic parser rather than crashing
        req = parse_request("Hotel in Bengaluru from 20 to 21 Nov 2026 for 2 guests")
        assert req.destination == "Bengaluru"
        assert req.check_in == "2026-11-20"
        assert req.check_out == "2026-11-21"
