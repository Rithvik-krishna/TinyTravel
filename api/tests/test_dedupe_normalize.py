"""Tests for hotel deduplication, multi-platform matching, normalization, and target selection."""
import asyncio
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.dedupe import (
    normalize_name,
    confidence,
    match_status,
    group_listings,
    AUTO_MERGE_THRESHOLD,
    SUGGESTED_THRESHOLD,
)
from services.normalize import (
    normalize_meal_plan,
    comparable_key,
    comparable_sets,
    select_targets,
)
from agents.discovery import discover, build_discovery_goal

demo_path = Path(__file__).resolve().parents[2] / "fixtures" / "demo_run.json"
demo_data = json.loads(demo_path.read_text(encoding="utf-8"))


# --- 1. Deduplication and Grouping Tests ---

def test_golden_grouping_from_fixture():
    groups = group_listings(demo_data["listings"])
    assert len(groups) == 3

    g1, g2, g3 = groups[0], groups[1], groups[2]

    # Hotel 1: La Marvella
    assert g1["hotel_id"] == "h1"
    assert g1["canonical_name"] == "La Marvella"
    assert g1["area"] == "HSR Layout"
    assert g1["match_status"] == "merged"
    assert g1["confidence"] >= 0.90
    assert len(g1["offer_ids"]) == 3
    assert set(g1["offer_ids"]) == {"h1_cleartrip", "h1_agoda", "h1_booking"}

    # Hotel 2: Lemon Leaf Suites
    assert g2["hotel_id"] == "h2"
    assert g2["canonical_name"] == "Lemon Leaf Suites"
    assert g2["area"] == "Koramangala"
    assert g2["match_status"] == "merged"
    assert g2["confidence"] >= 0.90
    assert len(g2["offer_ids"]) == 3
    assert set(g2["offer_ids"]) == {"h2_cleartrip", "h2_agoda", "h2_booking"}

    # Hotel 3: Urban Nest Inn (Suggested, not merged)
    assert g3["hotel_id"] == "h3"
    assert g3["canonical_name"] == "Urban Nest Inn"
    assert g3["area"] == "HSR Layout"
    assert g3["match_status"] == "suggested"
    assert 0.75 <= g3["confidence"] <= 0.89
    assert len(g3["offer_ids"]) == 2
    assert set(g3["offer_ids"]) == {"h3_cleartrip", "h3_booking"}
    assert "Possible match: not merged in pricing" in g3["why"]


def test_threshold_exact_boundaries():
    assert match_status(0.90) == "merged"
    assert match_status(0.899) == "suggested"
    assert match_status(0.75) == "suggested"
    assert match_status(0.749) == "separate"
    assert match_status(1.0) == "merged"
    assert match_status(0.0) == "separate"


def test_normalize_name():
    assert normalize_name("The Taj Hotel & Resort") == "the taj"
    assert normalize_name("  Hotel  Urban  Nest   Inn & Suites  ") == "urban nest inn and suites"
    assert normalize_name("Lemon Leaf Suites, Koramangala - Hotel") == "lemon leaf suites koramangala"
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


def test_confidence_phone_and_geo_signals():
    # Identical with matching phone -> strong confidence
    a = {"hotel_name": "Grand Stay", "area": "Indiranagar", "phone": "08012345678"}
    b = {"hotel_name": "Grand Stay", "area": "Indiranagar", "phone": "08012345678"}
    assert confidence(a, b) == 1.0

    # Conflicting phone penalty
    c = {"hotel_name": "Grand Stay", "area": "Indiranagar", "phone": "08099999999"}
    assert confidence(a, c) < confidence(a, b)

    # Geo distance close (<200m)
    loc_a = {"hotel_name": "City Inn", "lat": 12.9716, "lng": 77.5946}
    loc_b = {"hotel_name": "City Inn", "lat": 12.9718, "lng": 77.5948}
    assert confidence(loc_a, loc_b) == 1.0

    # Geo distance far (>10km)
    loc_far = {"hotel_name": "City Inn", "lat": 13.1000, "lng": 77.8000}
    assert confidence(loc_a, loc_far) < confidence(loc_a, loc_b)


def test_group_listings_empty():
    assert group_listings([]) == []


# --- 2. Normalization and Target Selection Tests ---

def test_comparable_key_and_sets():
    off1 = {
        "max_occupancy": 2,
        "nights": 1,
        "meal_plan": "Breakfast included",
        "cancellation_category": "free",
    }
    off2 = {
        "max_occupancy": 2,
        "nights": 1,
        "meal_plan": "Free Breakfast",
        "cancellation_category": "free",
    }
    off3 = {
        "max_occupancy": 2,
        "nights": 1,
        "meal_plan": "Room only",
        "cancellation_category": "non_refundable",
    }

    key1 = comparable_key(off1)
    key2 = comparable_key(off2)
    key3 = comparable_key(off3)

    assert key1 == key2 == (2, 1, "breakfast", "free")
    assert key3 == (2, 1, "room_only", "non_refundable")

    sets = comparable_sets([off1, off2, off3])
    assert len(sets) == 2
    assert len(sets[key1]) == 2
    assert len(sets[key3]) == 1


def test_select_targets_rules():
    groups = [
        # h1: merged, 3 platforms
        {"hotel_id": "h1", "canonical_name": "Hotel Alpha", "match_status": "merged", "offer_ids": ["h1_ct", "h1_ag", "h1_bk"]},
        # h2: merged, 2 platforms
        {"hotel_id": "h2", "canonical_name": "Hotel Beta", "match_status": "merged", "offer_ids": ["h2_ct", "h2_ag"]},
        # h3: suggested (unmerged) -> MUST BE EXCLUDED
        {"hotel_id": "h3", "canonical_name": "Hotel Gamma", "match_status": "suggested", "offer_ids": ["h3_ct", "h3_bk"]},
        # h4: merged, 1 platform only -> MUST BE EXCLUDED
        {"hotel_id": "h4", "canonical_name": "Hotel Delta", "match_status": "merged", "offer_ids": ["h4_ct"]},
    ]

    targets = select_targets(groups, max_hotels=3)
    # Only h1 and h2 are eligible
    assert len(targets) == 2
    assert targets[0]["hotel_id"] == "h1"  # 3 platforms preferred over 2
    assert targets[1]["hotel_id"] == "h2"


def test_select_targets_with_fewer_than_max():
    groups = [
        {"hotel_id": "h1", "canonical_name": "Solo Target", "match_status": "merged", "offer_ids": ["h1_ct", "h1_ag"]},
    ]
    targets = select_targets(groups, max_hotels=3)
    assert len(targets) == 1
    assert targets[0]["hotel_id"] == "h1"


def test_select_targets_empty():
    assert select_targets([]) == []


# --- 3. Discovery Agent Tests ---

def test_discovery_goal_construction():
    req = {"destination": "Bengaluru", "check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2, "rooms": 1}
    goal = build_discovery_goal(req)
    assert "Search for hotels in Bengaluru" in goal
    assert "STOP on the search results page" in goal
    assert "Never select a room, never enter checkout" in goal


def test_discovery_fake_mode(monkeypatch):
    monkeypatch.setenv("TINYFISH_FAKE", "1")
    req = {"destination": "Bengaluru"}

    listings_ct = asyncio.run(discover("cleartrip", req))
    assert len(listings_ct) == 3
    assert all(l["platform"] == "Cleartrip" for l in listings_ct)

    listings_ag = asyncio.run(discover("agoda", req))
    assert len(listings_ag) == 2
    assert all(l["platform"] == "Agoda" for l in listings_ag)

    listings_bk = asyncio.run(discover("booking", req))
    assert len(listings_bk) == 3
    assert all(l["platform"] == "Booking.com" for l in listings_bk)
