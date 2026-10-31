"""Offer normalization and comparable filtering service.
Groups offers into strictly comparable subsets (guests, nights, meal plan, cancellation)
and selects multi-platform target hotels for checkout verification.
"""
from typing import Optional, Union

try:
    from .scoring import non_comparable_warnings
except ImportError:
    from services.scoring import non_comparable_warnings


def normalize_meal_plan(meal_plan: Optional[str]) -> str:
    """Normalize free-text meal plan into standardized categories."""
    if not meal_plan or not meal_plan.strip():
        return "room_only"
    mp = meal_plan.lower()
    if "breakfast" in mp:
        return "breakfast"
    elif "dinner" in mp or "half board" in mp or "half-board" in mp:
        return "half_board"
    elif "all inclusive" in mp or "all-inclusive" in mp:
        return "all_inclusive"
    elif "room only" in mp or "bed only" in mp:
        return "room_only"
    return mp.strip()


def comparable_key(offer: dict) -> tuple:
    """Extract comparison tuple (occupancy, nights, meal_plan, cancellation_category).
    
    Two offers are comparable if and only if their comparable_keys are identical.
    """
    occupancy = int(offer.get("max_occupancy") or 2)
    nights = int(offer.get("nights") or 1)
    meal = normalize_meal_plan(offer.get("meal_plan"))
    cancellation = offer.get("cancellation_category") or "unknown"
    return (occupancy, nights, meal, cancellation)


def comparable_sets(group_offers: list[dict]) -> dict[tuple, list[dict]]:
    """Group offers for a hotel into sets of strictly comparable products."""
    sets: dict[tuple, list[dict]] = {}
    for o in group_offers:
        key = comparable_key(o)
        sets.setdefault(key, []).append(o)
    return sets


def select_targets(
    groups: list[dict],
    max_hotels: int = 3,
    budget_per_night: Optional[float] = None,
    listings: Optional[list[dict]] = None,
) -> list[dict]:
    """Select candidate hotels for deep checkout verification.
    
    Rules:
    - Must be merged (suggested / unmerged groups are NOT selected as multi-platform hotels)
    - Must be present on >= 2 platforms, prefer 3 platforms
    - Within budget_per_night on shown price (if budget specified)
    - Stable deterministic ordering: platform count desc, lowest shown price asc, canonical_name asc
    - Returns up to max_hotels target groups
    """
    if not groups:
        return []

    # Map hotel_id to member listings if available to inspect shown_price
    listings_by_hotel: dict[str, list[dict]] = {}
    if listings:
        for l in listings:
            hid = l.get("hotel_id")
            if hid:
                listings_by_hotel.setdefault(hid, []).append(l)

    eligible = []
    for g in groups:
        # 1. Suggested groups are never selected as multi-platform verification targets
        if g.get("match_status") != "merged":
            continue

        # 2. Must be present on >= 2 platforms
        offer_ids = g.get("offer_ids") or []
        platforms = set()
        for oid in offer_ids:
            # offer_id format: h1_cleartrip -> platform: cleartrip
            parts = oid.split("_", 1)
            if len(parts) == 2:
                platforms.add(parts[1])
            else:
                platforms.add(oid)

        platform_count = len(platforms)
        if platform_count < 2:
            continue

        # 3. Budget check on shown_price
        hid = g.get("hotel_id", "")
        group_listings = listings_by_hotel.get(hid, [])
        prices = [
            float(l["shown_price"])
            for l in group_listings
            if l.get("shown_price") is not None
        ]
        min_price = min(prices) if prices else 0.0

        if budget_per_night is not None and prices:
            # If all prices exceed budget, skip
            if min_price > budget_per_night:
                continue

        eligible.append({
            "group": g,
            "platform_count": platform_count,
            "min_price": min_price,
            "canonical_name": g.get("canonical_name", ""),
        })

    # Stable ordering: prefer 3 platforms over 2, then lower price, then alphabetical
    eligible.sort(
        key=lambda item: (-item["platform_count"], item["min_price"], item["canonical_name"])
    )

    return [item["group"] for item in eligible[:max_hotels]]
