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


def discovery_start_url(platform: str, req: dict) -> str:
    """Where a discovery agent starts.

    A guessed results-page URL (e.g. Cleartrip ?city=Delhi) does not work for city names and the agent stalls
    on it, so Cleartrip and Agoda start from their hotel search page and type the city. Booking.com accepts
    a direct search URL.
    """
    p = platform.lower().replace(".", "").replace(" ", "").replace("-", "")
    if p == "cleartrip":
        return "https://www.cleartrip.com/hotels"
    if p == "agoda":
        return "https://www.agoda.com/"
    if p in ("booking", "bookingcom"):
        city = quote_plus(req.get("destination", "Bengaluru"))
        return (
            "https://www.booking.com/searchresults.html"
            f"?ss={city}&checkin={req.get('check_in', '2026-11-20')}&checkout={req.get('check_out', '2026-11-21')}"
            f"&group_adults={req.get('guests', 2)}&no_rooms={req.get('rooms', 1)}&selected_currency=INR"
        )
    return site_url(platform, req)


def build_discovery_goal(req: dict, platform: str = "") -> str:
    """Construct goal prompt for search listing extraction without checkout."""
    city = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = req.get("guests", 2)
    rooms = req.get("rooms", 1)
    p = platform.lower().replace(".", "").replace(" ", "").replace("-", "")

    if p in ("booking", "bookingcom"):
        how = (
            f"The page should already show hotel search results for {city}. If a sign-in prompt or pop-up appears, close it. "
            f"If results are not shown, search for {city} for {check_in} to {check_out}, {guests} adults, {rooms} room."
        )
    else:
        how = (
            f"Open the hotel search form. Type {city} in the destination box and pick the first matching city suggestion. "
            f"Set check-in {check_in} and check-out {check_out}, {guests} adults, {rooms} room, then press Search. "
            "Close any pop-up or login prompt that appears (do not log in)."
        )

    return (
        f"{how}\n"
        "When hotel results are shown, extract up to 8 hotels from the first page. Do not scroll more than twice.\n"
        "For each hotel, extract: hotel_name, address, area, lat, lng, phone, rating (numeric score out of 5), "
        "shown_price (the initial total or nightly price shown on the card), currency, and source_url (the direct link to the hotel).\n"
        "Missing fields must be null, never guessed or fabricated.\n"
        "STOP on the search results page. Never select a room, never enter checkout, never enter payment or login details.\n"
        "Use at most 25 steps. Return ONLY JSON in the given schema."
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


def _clean(value: Any, *, zero_is_null: bool = False) -> Any:
    """Agents sometimes return the text "null" or 0 for unknown values. Unknown must be null, never 0."""
    if isinstance(value, str) and value.strip().lower() in ("", "null", "none", "n/a", "unknown"):
        return None
    if zero_is_null and isinstance(value, (int, float)) and value == 0:
        return None
    return value


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
    url = explicit_url if explicit_url else discovery_start_url(platform, req)

    goal = build_discovery_goal(req, platform)
    schema = DiscoveryResult.model_json_schema()

    run: AgentRun = await run_agent(
        url=url,
        goal=goal,
        output_schema=schema,
        profile=profile,
        timeout_s=req.get("timeout_s", int(os.getenv("DISCOVERY_TIMEOUT_S", "900"))),
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
                "address": _clean(item.get("address")),
                "area": _clean(item.get("area")),
                "lat": _clean(item.get("lat"), zero_is_null=True),
                "lng": _clean(item.get("lng"), zero_is_null=True),
                "phone": _clean(item.get("phone")),
                "rating": _clean(item.get("rating"), zero_is_null=True),
                "shown_price": _clean(item.get("shown_price"), zero_is_null=True),
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
