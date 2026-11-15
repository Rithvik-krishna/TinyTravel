"""
Unit tests for Gemini fallback extraction.
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from api.services.gemini_fallback import (
    is_gemini_fallback_enabled,
    extract_with_gemini_fallback,
)


def test_is_gemini_fallback_enabled(monkeypatch):
    monkeypatch.delenv("GEMINI_FALLBACK_EXTRACTION", raising=False)
    assert is_gemini_fallback_enabled() is False

    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "true")
    assert is_gemini_fallback_enabled() is True

    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "1")
    assert is_gemini_fallback_enabled() is True

    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "false")
    assert is_gemini_fallback_enabled() is False


def test_extract_fallback_disabled_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "false")
    res = extract_with_gemini_fallback("Sample text")
    assert res is None


def test_extract_fallback_missing_key_returns_none(monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    res = extract_with_gemini_fallback("Sample text")
    assert res is None


def test_extract_fallback_success(monkeypatch):
    monkeypatch.setenv("GEMINI_FALLBACK_EXTRACTION", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_test_key")

    mock_gemini_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "price_final_payable": 11495.0,
                                "fee_lines": [
                                    {"label": "Base Room Rate", "amount": 8429.0, "fee_kind": "other"},
                                    {"label": "Taxes & Fees", "amount": 3066.0, "fee_kind": "tax"},
                                ],
                                "room_type": "Deluxe Room",
                                "meal_plan": "Room with Breakfast",
                                "cancellation_policy": "Free cancellation"
                            })
                        }
                    ]
                }
            }
        ]
    }

    class MockHTTPResponse:
        def read(self):
            return json.dumps(mock_gemini_resp).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    with patch("urllib.request.urlopen", return_value=MockHTTPResponse()):
        res = extract_with_gemini_fallback("Payment summary: Total payable ₹11,495", "La Marvella", "Cleartrip")
        assert res is not None
        assert res["price_final_payable"] == 11495.0
        assert len(res["fee_lines"]) == 2
        assert res["fee_lines"][0]["amount"] == 8429.0
        assert res["fee_lines"][1]["fee_kind"] == "tax"
        assert res["room_type"] == "Deluxe Room"
        assert res["extracted_by"] == "gemini_fallback"
