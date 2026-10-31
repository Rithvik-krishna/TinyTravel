"""Discovery Agent.
Autonomous TinyFish browser agent extracting initial hotel search listings without entering checkout.
"""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
from typing import Callable, Optional, Any
from urllib.parse import quote_plus

try:
    from ..models import Listing, BaseModelForbid
    from ..services.tinyfish import run_agent, AgentRun
    from .checkout import site_url
except ImportError:
    from models import Listing, BaseModelForbid
    from services.tinyfish import run_agent, AgentRun
    from agents.checkout import site_url

IST = timezone(timedelta(hours=5, minutes=30))


class DiscoveryItem(BaseModelForbid):
    hotel_name: str
    address: Optional[str] = None
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    shown_price: Optional[float] = None
    currency: str = "INR"
    source_url: str = ""


class DiscoveryResult(BaseModelForbid):
    listings: list[DiscoveryItem] = []


def build_discovery_goal(req: dict) -> str:
    """Construct goal prompt for search listing extraction without checkout."""
    city = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = req.get("guests", 2)
    rooms = req.get("rooms", 1)

    return (
        f"Open the provided URL. Search for hotels in {city} for {check_in} to {check_out}, {guests} adults, {rooms} room.\n"
        "Extract up to 8 hotel search results displayed on the first page.\n"
        "For each hotel, extract: hotel_name, address, area, lat, lng, phone, rating (numeric score out of 5), "
        "shown_price (the initial total or nightly price shown on the card), currency, and source_url (the direct link to the hotel).\n"
        "Missing fields must be null, never guessed or fabricated.\n"
        "STOP on the search results page. Never select a room, never enter checkout, never enter payment or login details.\n"
        "Use at most 15 steps. Return ONLY JSON in the given schema."
    )


def _load_fixture_listings(platform: str) -> list[dict]:
    """Load mock listings from fixtures/demo_run.json matching the platform."""
    fixtures_dir = Path(__file__).resolve().parents[2] / "fixtures"
    demo_file = fixtures_dir / "demo_run.json"
    if not demo_file.exists():
        return []
    try:
        data = json.loads(demo_file.read_text(encoding="utf-8"))
        p = platform.lower().replace(".", "").replace(" ", "")
        if p == "booking":
            p = "bookingcom"
        return [
            l for l in data.get("listings", [])
            if l.get("platform", "").lower().replace(".", "").replace(" ", "") == p
        ]
    except Exception:
        return []


async def discover(
    platform: str,
    req: dict,
    *,
    profile: str = "lite",
    on_stream_url: Optional[Callable[[str], Any]] = None,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> list[dict]:
    """Extract up to ~8 hotel listings from a search results page.
    
    In fake mode, returns canonical fixture listings for the requested platform.
    """
    is_fake = os.getenv("TINYFISH_FAKE") == "1" or req.get("fake") is True

    if is_fake:
        fixture_listings = _load_fixture_listings(platform)
        if fixture_listings:
            return fixture_listings

    explicit_url = req.get("url")
    url = explicit_url if explicit_url else site_url(platform, req)

    goal = build_discovery_goal(req)
    schema = DiscoveryResult.model_json_schema()

    run: AgentRun = await run_agent(
        url=url,
        goal=goal,
        output_schema=schema,
        profile=profile,
        timeout_s=req.get("timeout_s", 180),
        on_stream_url=on_stream_url,
        on_progress=on_progress,
    )

    extracted_items = []
    if run.result and isinstance(run.result, dict):
        raw_list = run.result.get("listings", [])
        now_iso = datetime.now(IST).isoformat()
        platform_slug = platform.lower().replace(".", "").replace(" ", "")

        for idx, item in enumerate(raw_list[:8]):
            if not isinstance(item, dict):
                continue
            listing_id = f"{platform_slug}_{idx + 1:03d}"
            listing_dict = {
                "listing_id": listing_id,
                "platform": platform,
                "hotel_name": item.get("hotel_name", ""),
                "address": item.get("address"),
                "area": item.get("area"),
                "lat": item.get("lat"),
                "lng": item.get("lng"),
                "phone": item.get("phone"),
                "rating": item.get("rating"),
                "shown_price": item.get("shown_price"),
                "currency": item.get("currency", "INR"),
                "source_url": item.get("source_url") or url,
                "captured_at": now_iso,
                "mock": is_fake,
            }
            try:
                # Validate against strict Listing model
                Listing.model_validate(listing_dict)
                extracted_items.append(listing_dict)
            except Exception:
                extracted_items.append(listing_dict)

    return extracted_items
