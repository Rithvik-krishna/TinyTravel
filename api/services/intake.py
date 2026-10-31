"""Intake Service for parsing natural language travel queries.
Supports Anthropic Claude LLM parsing when ANTHROPIC_API_KEY is configured,
with a robust deterministic heuristic fallback for offline/local execution.
"""
from datetime import datetime, date
import json
import os
import re
from typing import Optional

try:
    from ..models import SearchRequestOut, DealMode
except ImportError:
    from models import SearchRequestOut, DealMode

DEFAULT_INTAKE_MODEL = "claude-3-5-sonnet-20241022"


def _parse_month(m_str: str) -> int:
    months = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    return months.get(m_str.lower()[:3], 11)


def parse_offline_heuristics(text: str) -> dict:
    """Deterministic regex & heuristic parser for travel requests."""
    t = text.strip()
    tl = t.lower()

    # 0. Recognition check: verify query has recognizable travel intent, destination, dates, or hotel keywords
    common_cities = ["bengaluru", "bangalore", "mumbai", "delhi", "goa", "hyderabad", "chennai", "jaipur", "kolkata", "pune", "kochi", "agra"]
    travel_keywords = [
        "hotel", "stay", "room", "resort", "inn", "suites", "villa", "guest", "guests",
        "night", "nights", "booking", "trip", "travel", "budget", "checkin", "checkout",
        "check-in", "check-out", "breakfast", "cancellation", "marvella", "lemon", "la marvella"
    ]
    has_city = any(city in tl for city in common_cities)
    has_travel_kw = any(kw in tl for kw in travel_keywords)
    has_date = bool(re.search(r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*([a-zA-Z]+)", tl) or re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t))

    if not (has_city or has_travel_kw or has_date):
        raise ValueError("Unrecognized query: please provide a destination (e.g. 'Bengaluru'), dates, or hotel name.")

    # 1. Destination
    destination = "Bengaluru"
    for city in common_cities:
        if city in tl:
            destination = "Bengaluru" if city in ("bengaluru", "bangalore") else city.title()
            break

    # 2. Area hint
    area_hint = None
    if "hsr" in tl and "koramangala" in tl:
        area_hint = "HSR Layout / Koramangala"
    elif "hsr" in tl:
        area_hint = "HSR Layout"
    elif "koramangala" in tl:
        area_hint = "Koramangala"
    elif "indiranagar" in tl:
        area_hint = "Indiranagar"
    elif "whitefield" in tl:
        area_hint = "Whitefield"
    elif "electronic city" in tl:
        area_hint = "Electronic City"

    # 3. Dates (default year 2026)
    check_in = None
    check_out = None

    # Pattern: 10-12 Jan 2020 or 20-21 Nov or 20-21 November or 20 to 21 Nov
    m_range = re.search(r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*([a-zA-Z]+)(?:\s*(\d{4}))?", tl)
    if m_range:
        d1, d2, m_name = int(m_range.group(1)), int(m_range.group(2)), m_range.group(3)
        year = int(m_range.group(4)) if m_range.group(4) else 2026
        month = _parse_month(m_name)
        check_in = f"{year}-{month:02d}-{d1:02d}"
        check_out = f"{year}-{month:02d}-{d2:02d}"
    else:
        # Pattern: ISO dates YYYY-MM-DD
        iso_dates = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", t)
        if len(iso_dates) >= 2:
            check_in, check_out = iso_dates[0], iso_dates[1]
        elif len(iso_dates) == 1:
            check_in = iso_dates[0]
            # default 1 night
            cin_dt = datetime.strptime(check_in, "%Y-%m-%d").date()
            cout_dt = date(cin_dt.year, cin_dt.month, cin_dt.day + 1)
            check_out = cout_dt.isoformat()

    if not check_in or not check_out:
        # Default fallback date in 2026
        check_in = "2026-11-20"
        check_out = "2026-11-21"

    # 4. Guests & Rooms
    guests = 2
    if "solo" in tl or "1 person" in tl or "1 guest" in tl or "1 adult" in tl:
        guests = 1
    elif "couple" in tl or "2 people" in tl or "2 guests" in tl or "2 adults" in tl or "2 persons" in tl:
        guests = 2
    else:
        m_guests = re.search(r"(\d+)\s*(?:people|guests|adults|persons)", tl)
        if m_guests:
            guests = int(m_guests.group(1))

    rooms = 1
    m_rooms = re.search(r"(\d+)\s*rooms?", tl)
    if m_rooms:
        rooms = int(m_rooms.group(1))

    # 5. Budget per night
    budget_per_night = None
    # Matches "under 12k", "under 12000", "<12k", "12k", "budget 0", "budget 12000", "under 12,000"
    budget_matches = re.finditer(r"(?:under|budget|below|<|upto|max)\s*(?:rs\.?|inr)?\s*(-?\d+(?:,\d+)?(?:\.\d+)?)\s*(k|thousand)?\b", tl)
    found_budget = None
    for bm in budget_matches:
        raw_num = bm.group(1).replace(",", "")
        unit = bm.group(2)
        try:
            val = float(raw_num)
        except ValueError:
            continue
        if unit == "k" or (unit is None and 0 < val < 100):
            val *= 1000
        found_budget = val
        break

    if found_budget is None:
        # Try standalone 12k or 15k
        m_k = re.search(r"\b(\d+)\s*k\b", tl)
        if m_k:
            found_budget = float(m_k.group(1)) * 1000

    if found_budget is not None:
        budget_per_night = found_budget

    # 6. Must-haves
    must_have = {
        "breakfast": bool("breakfast" in tl),
        "free_cancellation": bool("free cancellation" in tl or "refundable" in tl),
        "wifi": bool("wifi" in tl or "wi-fi" in tl),
        "parking": bool("parking" in tl),
    }

    # 7. Deal mode
    deal_mode = "best_value"
    if "cheapest" in tl or "lowest price" in tl or "lowest-price" in tl:
        deal_mode = "lowest_price"
    elif "transparent" in tl or "transparency" in tl:
        deal_mode = "most_transparent"

    return {
        "destination": destination,
        "area_hint": area_hint,
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "rooms": rooms,
        "budget_per_night": budget_per_night,
        "must_have": must_have,
        "deal_mode": deal_mode,
        "currency": "INR",
        "mock": False,
        "raw_text": t,
    }


def validate_search_request(data: dict) -> None:
    """Validate search request invariants according to project rules."""
    check_in_str = data.get("check_in")
    check_out_str = data.get("check_out")

    if not check_in_str or not check_out_str:
        raise ValueError("Both check_in and check_out dates are required.")

    try:
        cin = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        cout = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format (must be YYYY-MM-DD): {e}")

    # Check-in date in the future (relative to base date or 2026 timeline)
    # The project event is Oct 31, 2026.
    if cin < date(2026, 1, 1):
        raise ValueError(f"Check-in date {cin} must be in the future.")

    if cout <= cin:
        raise ValueError(f"Check-out date ({cout}) must be after check-in date ({cin}).")

    guests = data.get("guests", 1)
    if guests < 1:
        raise ValueError(f"Guests must be >= 1, got {guests}.")

    rooms = data.get("rooms", 1)
    if rooms < 1:
        raise ValueError(f"Rooms must be >= 1, got {rooms}.")

    budget = data.get("budget_per_night")
    if budget is not None and budget <= 0:
        raise ValueError(f"Budget per night must be > 0, got {budget}.")


def parse_request_llm(text: str, api_key: str, model_name: str) -> dict:
    """Parse search query using Anthropic Messages API."""
    import urllib.request
    import ssl

    prompt = (
        "You are the travel intake parser for TinyTravel.\n"
        "Parse the user's natural language hotel query into a strict JSON object with fields:\n"
        "- destination (str, default 'Bengaluru')\n"
        "- area_hint (str or null, e.g. 'HSR Layout / Koramangala')\n"
        "- check_in (str 'YYYY-MM-DD', default year 2026)\n"
        "- check_out (str 'YYYY-MM-DD', default year 2026)\n"
        "- guests (int >= 1, default 2)\n"
        "- rooms (int >= 1, default 1)\n"
        "- budget_per_night (float or null, in INR, e.g. 12k -> 12000)\n"
        "- must_have (dict with bool keys: breakfast, free_cancellation, parking, wifi)\n"
        "- deal_mode (one of: 'lowest_price', 'best_value', 'most_transparent', default 'best_value')\n"
        "- currency (str, default 'INR')\n"
        "Return ONLY the JSON object."
    )

    req_data = {
        "model": model_name,
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": f"{prompt}\n\nQuery: {text}"}
        ],
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(req_data).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        content_blocks = res_json.get("content", [])
        raw_text_out = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        # Extract JSON from potential code fences
        match = re.search(r"\{.*\}", raw_text_out, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            parsed["raw_text"] = text
            parsed["mock"] = False
            return parsed
        raise ValueError("Could not parse JSON from Anthropic response.")


def parse_request(text: str) -> SearchRequestOut:
    """Parse natural language query into a validated SearchRequestOut model."""
    if not text or not text.strip():
        raise ValueError("Query text cannot be empty.")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    model_name = os.getenv("INTAKE_MODEL", DEFAULT_INTAKE_MODEL)

    data = None
    if api_key:
        try:
            data = parse_request_llm(text, api_key, model_name)
        except Exception:
            # Fall back safely to offline heuristics
            data = None

    if data is None:
        data = parse_offline_heuristics(text)

    # Validate constraints
    validate_search_request(data)

    # Return validated Pydantic model
    return SearchRequestOut.model_validate(data)
