"""TinyFish SDK service integration.
Single integration point for all browser agent runs.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import logging
import os
from pathlib import Path
import re
from typing import Callable, Literal, Optional, Any
from dotenv import load_dotenv

# Load local .env if present
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
load_dotenv(override=True)

logger = logging.getLogger("tinyfish")

IST = timezone(timedelta(hours=5, minutes=30))

REDACT_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]{8,}", re.IGNORECASE),
    re.compile(r"gho_[a-zA-Z0-9_\-]{8,}", re.IGNORECASE),
    re.compile(r"TINYFISH_API_KEY\s*=\s*[^\s]+", re.IGNORECASE),
    re.compile(r"api[_-]?key[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9_\-]{8,}[\"']?", re.IGNORECASE),
]


def redact(text: str) -> str:
    """Mask sensitive tokens and keys in log strings."""
    if not isinstance(text, str):
        return text
    env_key = os.getenv("TINYFISH_API_KEY")
    if env_key and len(env_key) > 4:
        text = text.replace(env_key, "[REDACTED]")
    for pattern in REDACT_PATTERNS:
        text = pattern.sub(r"[REDACTED]", text)
    return text


@dataclass
class AgentRun:
    run_id: str
    streaming_url: Optional[str]
    status: Literal["completed", "failed", "timeout"]
    result: Optional[dict]
    raw: dict
    steps: int
    cost_usd: float
    started_at: str
    finished_at: str
    error: Optional[str] = None
    cost_estimated: bool = False


def _load_demo_offers() -> list[dict]:
    fixtures_dir = Path(__file__).resolve().parents[2] / "fixtures"
    demo_file = fixtures_dir / "demo_run.json"
    if demo_file.exists():
        try:
            return json.loads(demo_file.read_text(encoding="utf-8")).get("offers", [])
        except Exception:
            pass
    return []


def _match_demo_offer(url: str, goal: str, offers: list[dict]) -> dict:
    url_l = url.lower()
    goal_l = goal.lower()

    # Determine site
    site = None
    if "cleartrip" in url_l or "cleartrip" in goal_l:
        site = "Cleartrip"
    elif "agoda" in url_l or "agoda" in goal_l:
        site = "Agoda"
    elif "booking" in url_l or "booking" in goal_l:
        site = "Booking.com"

    # Determine hotel
    hotel = None
    if "marvella" in goal_l or "marvella" in url_l:
        hotel = "La Marvella"
    elif "lemon" in goal_l or "lemon" in url_l:
        hotel = "Lemon Leaf Suites"
    elif "urban" in goal_l or "urban" in url_l:
        hotel = "Urban Nest"

    for o in offers:
        o_site = o.get("site")
        o_hotel = o.get("hotel_name", "")
        if site and o_site != site:
            continue
        if hotel and hotel.lower() not in o_hotel.lower():
            continue
        return o

    # Default fallback
    return offers[0] if offers else {}


async def _run_fake_agent(
    url: str,
    goal: str,
    output_schema: Optional[dict],
    profile: str,
    timeout_s: float,
    on_stream_url: Optional[Callable],
    on_progress: Optional[Callable],
) -> AgentRun:
    started_at = datetime.now(IST).isoformat()
    offers = _load_demo_offers()
    offer = _match_demo_offer(url, goal, offers)

    site_slug = offer.get("site", "cleartrip").lower().replace(".", "").replace(" ", "")
    if "cleartrip" in site_slug:
        site_slug = "cleartrip"
    elif "agoda" in site_slug:
        site_slug = "agoda"
    elif "booking" in site_slug:
        site_slug = "booking"

    streaming_url = f"/mock/tile-{site_slug}.html"
    if on_stream_url:
        res = on_stream_url(streaming_url)
        if asyncio.iscoroutine(res):
            await res

    fake_speed = float(os.getenv("FAKE_SPEED", "0.01"))
    steps = [
        "Opening search page",
        "Searching hotel by name",
        "Opening hotel page",
        "Selecting room",
        "Entering guest details (dummy)",
        "Reached payment page, stopping",
    ]

    offer_status = offer.get("status", "verified")
    furthest = offer.get("furthest_step", "payment")

    if offer_status == "blocked":
        steps = ["Opening search page", "Searching hotel by name", "Encountered CAPTCHA challenge"]
    elif offer_status == "unverified":
        steps = ["Opening search page", "Searching hotel by name", "Opening hotel page", "Selecting room"]

    for step_text in steps:
        await asyncio.sleep(fake_speed)
        if on_progress:
            res = on_progress(step_text)
            if asyncio.iscoroutine(res):
                await res

    finished_at = datetime.now(IST).isoformat()
    step_count = len(steps)
    cost = offer.get("cost_usd", round(step_count * 0.016, 4))

    # Build ProbeResult dictionary from offer
    probe_keys = [
        "site", "reached_payment_page", "furthest_step", "blocker",
        "hotel_name", "hotel_url", "room_type", "max_occupancy",
        "meal_plan", "cancellation_policy", "price_shown_on_listing",
        "price_shown_on_room_selection", "price_final_payable",
        "fee_lines", "preselected_addons", "urgency_or_scarcity_messages",
        "price_trail", "currency", "notes",
    ]
    result_data = {k: offer[k] for k in probe_keys if k in offer}

    if offer_status == "verified":
        status: Literal["completed", "failed", "timeout"] = "completed"
        error = None
    elif offer_status == "blocked":
        status = "failed"
        error = f"Blocked by {offer.get('blocker', 'unknown')}"
    else:
        status = "failed"
        error = f"Unverified: stopped at {furthest}"

    return AgentRun(
        run_id=offer.get("run_id", f"mock_run_{offer.get('offer_id', 'unknown')}"),
        streaming_url=streaming_url,
        status=status,
        result=result_data,
        raw=offer,
        steps=step_count,
        cost_usd=cost,
        cost_estimated=False,
        started_at=started_at,
        finished_at=finished_at,
        error=error,
    )


def clean_schema_for_tinyfish(schema: Optional[dict]) -> Optional[dict]:
    """Clean a JSON schema for TinyFish API compatibility.
    
    TinyFish rejects schemas with:
    1. '$defs' (definitions must be inlined)
    2. 'additionalProperties'
    3. 'title'
    4. 'default'
    5. 'type: null' or 'anyOf' with null (collapsed to concrete non-null type)
    """
    if not schema or not isinstance(schema, dict):
        return schema

    import copy
    schema_copy = copy.deepcopy(schema)
    defs = schema_copy.pop("$defs", {})

    def _resolve(node):
        if isinstance(node, dict):
            while "$ref" in node:
                ref_path = node.pop("$ref")
                ref_name = ref_path.split("/")[-1]
                if ref_name in defs:
                    resolved = copy.deepcopy(defs[ref_name])
                    resolved.update(node)
                    node.clear()
                    node.update(resolved)
                else:
                    break

            if "anyOf" in node:
                non_null = [item for item in node["anyOf"] if item.get("type") != "null"]
                if len(non_null) == 1:
                    replacement = non_null[0]
                    node.pop("anyOf")
                    node.update(replacement)
                elif len(non_null) > 1:
                    node["anyOf"] = non_null

            node.pop("default", None)
            node.pop("title", None)
            node.pop("additionalProperties", None)

            for v in list(node.values()):
                _resolve(v)
        elif isinstance(node, list):
            for item in node:
                _resolve(item)

    _resolve(schema_copy)
    return schema_copy


async def run_agent(
    url: str,
    goal: str,
    output_schema: Optional[dict] = None,
    profile: str = "lite",
    timeout_s: float = 360,
    on_stream_url: Optional[Callable[[str], Any]] = None,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> AgentRun:
    """Execute a single TinyFish browser agent run.

    Supports live execution via TinyFish SDK or canned replay via TINYFISH_FAKE=1.
    """
    logger.info(redact(f"run_agent starting for url={url}, profile={profile}"))

    # Check fake mode
    is_fake = os.getenv("TINYFISH_FAKE") == "1"
    if is_fake:
        try:
            async with asyncio.timeout(timeout_s):
                return await _run_fake_agent(
                    url=url,
                    goal=goal,
                    output_schema=output_schema,
                    profile=profile,
                    timeout_s=timeout_s,
                    on_stream_url=on_stream_url,
                    on_progress=on_progress,
                )
        except TimeoutError:
            started_at = datetime.now(IST).isoformat()
            finished_at = started_at
            return AgentRun(
                run_id="fake_timeout",
                streaming_url=None,
                status="timeout",
                result=None,
                raw={"timeout": True},
                steps=0,
                cost_usd=0.0,
                started_at=started_at,
                finished_at=finished_at,
                error=f"Agent run timed out after {timeout_s}s",
                cost_estimated=True,
            )

    # Real live TinyFish execution (lazy SDK import)
    try:
        from tinyfish import TinyFish
    except ImportError as e:
        raise RuntimeError("tinyfish package is not installed.") from e

    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        raise ValueError("TINYFISH_API_KEY environment variable is not set.")

    # Clean schema for TinyFish API compatibility
    cleaned_output_schema = clean_schema_for_tinyfish(output_schema)

    loop = asyncio.get_running_loop()
    started_at = datetime.now(IST).isoformat()

    run_meta = {
        "run_id": "pending",
        "streaming_url": None,
        "steps": 0,
        "status": "completed",
        "result": None,
        "raw": {},
        "error": None,
    }

    def _sync_worker():
        c = TinyFish(api_key=api_key)

        def _handle_stream_url(event):
            url_str = getattr(event, "streaming_url", None)
            if url_str:
                run_meta["streaming_url"] = url_str
                if on_stream_url:
                    if asyncio.iscoroutinefunction(on_stream_url):
                        asyncio.run_coroutine_threadsafe(on_stream_url(url_str), loop)
                    else:
                        loop.call_soon_threadsafe(on_stream_url, url_str)

        def _handle_progress(event):
            purpose = getattr(event, "purpose", None) or "Progress step"
            run_meta["steps"] += 1
            if on_progress:
                if asyncio.iscoroutinefunction(on_progress):
                    asyncio.run_coroutine_threadsafe(on_progress(purpose), loop)
                else:
                    loop.call_soon_threadsafe(on_progress, purpose)

        capture_cfg = None
        try:
            from tinyfish import CaptureConfig
            capture_cfg = CaptureConfig(screenshots=True, recording=True)
        except Exception:
            pass

        with c.agent.stream(
            url=url,
            goal=goal,
            browser_profile=profile,
            output_schema=cleaned_output_schema,
            capture_config=capture_cfg,
            on_streaming_url=_handle_stream_url,
            on_progress=_handle_progress,
        ) as stream:
            for event in stream:
                if hasattr(event, "run_id") and event.run_id:
                    run_meta["run_id"] = event.run_id

                # CompleteEvent
                if hasattr(event, "result_json"):
                    raw_res = event.result_json
                    run_meta["raw"]["result_json"] = raw_res

                    err = getattr(event, "error", None)
                    if err:
                        run_meta["status"] = "failed"
                        run_meta["error"] = str(err)
                        run_meta["raw"]["error"] = str(err)

                    if raw_res is not None:
                        if isinstance(raw_res, dict):
                            run_meta["result"] = raw_res
                        elif isinstance(raw_res, str):
                            try:
                                run_meta["result"] = json.loads(raw_res)
                            except Exception as parse_err:
                                run_meta["status"] = "failed"
                                run_meta["error"] = f"Invalid JSON result: {parse_err}"
                                run_meta["raw"]["raw_text"] = raw_res
                        else:
                            run_meta["status"] = "failed"
                            run_meta["error"] = "Invalid result structure from agent"

    try:
        async with asyncio.timeout(timeout_s):
            await asyncio.to_thread(_sync_worker)
    except TimeoutError:
        finished_at = datetime.now(IST).isoformat()
        return AgentRun(
            run_id=run_meta["run_id"],
            streaming_url=run_meta["streaming_url"],
            status="timeout",
            result=None,
            raw={"timeout": True, "partial": run_meta["raw"]},
            steps=run_meta["steps"],
            cost_usd=round(run_meta["steps"] * 0.016, 4),
            started_at=started_at,
            finished_at=finished_at,
            error=f"Agent run timed out after {timeout_s}s",
            cost_estimated=True,
        )
    except Exception as exc:
        finished_at = datetime.now(IST).isoformat()
        logger.error(redact(f"TinyFish agent run failed: {exc}"))
        return AgentRun(
            run_id=run_meta["run_id"],
            streaming_url=run_meta["streaming_url"],
            status="failed",
            result=None,
            raw={"exception": str(exc)},
            steps=run_meta["steps"],
            cost_usd=round(run_meta["steps"] * 0.016, 4),
            started_at=started_at,
            finished_at=finished_at,
            error=str(exc),
            cost_estimated=True,
        )

    finished_at = datetime.now(IST).isoformat()
    return AgentRun(
        run_id=run_meta["run_id"],
        streaming_url=run_meta["streaming_url"],
        status=run_meta["status"],
        result=run_meta["result"],
        raw=run_meta["raw"],
        steps=run_meta["steps"],
        cost_usd=round(run_meta["steps"] * 0.016, 4),
        started_at=started_at,
        finished_at=finished_at,
        error=run_meta["error"],
        cost_estimated=True,
    )


async def get_balance() -> float | None:
    """Fetch current spendable balance in USD from TinyFish wallet."""
    if os.getenv("TINYFISH_FAKE") == "1" or os.getenv("DATA_MODE", "mock") == "mock":
        return 50.0

    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        return None

    try:
        from tinyfish import TinyFish

        def _fetch_balance():
            c = TinyFish(api_key=api_key)
            w = c.wallet.get()
            return float(w.available_balance)

        return await asyncio.to_thread(_fetch_balance)
    except Exception as exc:
        logger.warning(redact(f"Failed to fetch TinyFish wallet balance: {exc}"))
        return None
