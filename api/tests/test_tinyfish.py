import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.tinyfish import AgentRun, run_agent, get_balance, redact


def test_redact_masks_secrets():
    """Verify that redact() masks API keys, bearer tokens, and TINYFISH_API_KEY."""
    assert redact("User message without keys") == "User message without keys"
    assert redact("key: sk-1234567890abcdef12345") == "key: [REDACTED]"
    assert redact("TINYFISH_API_KEY=my_super_secret_key_123") == "[REDACTED]"
    assert redact("Bearer gho_dummyfaketoken1234567890abcdef") == "[REDACTED]"
    assert redact("api_key='abc123456789'") == "[REDACTED]"


def test_fake_mode_verified_offer():
    """Verify fake mode returns complete verified offer for Cleartrip + La Marvella."""
    os.environ["TINYFISH_FAKE"] = "1"
    os.environ["FAKE_SPEED"] = "0.001"

    stream_urls = []
    progress_steps = []

    def on_stream(url: str):
        stream_urls.append(url)

    def on_step(text: str):
        progress_steps.append(text)

    run = asyncio.run(run_agent(
        url="https://www.cleartrip.com/hotels/",
        goal="Find La Marvella in Bengaluru for 2 adults",
        output_schema={},
        on_stream_url=on_stream,
        on_progress=on_step,
    ))

    assert isinstance(run, AgentRun)
    assert run.status == "completed"
    assert run.error is None
    assert run.streaming_url == "/mock/tile-cleartrip.html"
    assert stream_urls == ["/mock/tile-cleartrip.html"]
    assert len(progress_steps) >= 3
    assert run.steps == len(progress_steps)
    assert run.result is not None
    assert run.result["hotel_name"] == "La Marvella"
    assert run.result["price_final_payable"] == 11276


def test_fake_mode_blocked_offer():
    """Verify fake mode reproduces deterministic blocked offer (Booking.com + Lemon Leaf)."""
    os.environ["TINYFISH_FAKE"] = "1"
    os.environ["FAKE_SPEED"] = "0.001"

    run = asyncio.run(run_agent(
        url="https://www.booking.com/hotels/",
        goal="Find Lemon Leaf Suites in Bengaluru",
        output_schema={},
    ))

    assert run.status == "failed"
    assert run.result["blocker"] == "captcha"
    assert run.result["reached_payment_page"] is False
    assert run.result["price_final_payable"] is None
    assert "Blocked" in run.error


def test_fake_mode_unverified_offer():
    """Verify fake mode reproduces deterministic unverified offer (Booking.com + Urban Nest)."""
    os.environ["TINYFISH_FAKE"] = "1"
    os.environ["FAKE_SPEED"] = "0.001"

    run = asyncio.run(run_agent(
        url="https://www.booking.com/hotels/",
        goal="Find Urban Nest Inn in Bengaluru",
        output_schema={},
    ))

    assert run.status == "failed"
    assert run.result["blocker"] == "timeout"
    assert run.result["reached_payment_page"] is False
    assert run.result["price_final_payable"] is None
    assert "Unverified" in run.error


def test_run_agent_timeout_handling():
    """Verify hard timeout triggers status='timeout' with no retries."""
    os.environ["TINYFISH_FAKE"] = "1"
    os.environ["FAKE_SPEED"] = "0.5"

    run = asyncio.run(run_agent(
        url="https://www.cleartrip.com/hotels/",
        goal="Find La Marvella",
        timeout_s=0.01,
    ))

    assert run.status == "timeout"
    assert "timed out after" in run.error


def test_invalid_json_handling():
    """Verify invalid JSON from agent sets status='failed' and preserves raw text."""
    orig_fake = os.environ.get("TINYFISH_FAKE")
    os.environ["TINYFISH_FAKE"] = "0"
    os.environ["TINYFISH_API_KEY"] = "sk-mock-key-for-test"

    try:
        mock_complete_event = MagicMock()
        mock_complete_event.run_id = "mock_run_bad_json"
        mock_complete_event.result_json = "{this is not valid json;}"
        mock_complete_event.error = None

        mock_stream = MagicMock()
        mock_stream.__enter__.return_value = [mock_complete_event]
        mock_stream.__exit__.return_value = False

        mock_client = MagicMock()
        mock_client.agent.stream.return_value = mock_stream

        with patch("tinyfish.TinyFish", return_value=mock_client):
            run = asyncio.run(run_agent(
                url="https://example.com",
                goal="test invalid json",
                timeout_s=5,
            ))

            assert run.status == "failed"
            assert run.result is None
            assert "Invalid JSON result" in run.error
            assert run.raw.get("raw_text") == "{this is not valid json;}"
    finally:
        if orig_fake is not None:
            os.environ["TINYFISH_FAKE"] = orig_fake
        else:
            os.environ.pop("TINYFISH_FAKE", None)


def test_get_balance_fake():
    """Verify get_balance() returns mock balance in fake/mock mode."""
    os.environ["TINYFISH_FAKE"] = "1"
    bal = asyncio.run(get_balance())
    assert bal == 50.0
