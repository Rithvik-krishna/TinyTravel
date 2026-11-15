import json
from pathlib import Path
import pytest
from api.models import Offer, ProbeResult
from api.services.normalize import (
    normalize_meal_plan,
    normalize_room_tier,
    cohort_key,
    are_offers_comparable,
)
from api.services.scoring import non_comparable_warnings


def test_normalize_room_tier():
    assert normalize_room_tier("Standard Double Room") == "standard"
    assert normalize_room_tier("Deluxe King Room") == "deluxe"
    assert normalize_room_tier("Superior Twin") == "deluxe"
    assert normalize_room_tier("Executive Club Suite") == "suite"  # suite takes precedence over executive
    assert normalize_room_tier("Executive Room") == "executive"
    assert normalize_room_tier("Presidential Penthouse") == "suite"
    assert normalize_room_tier("Luxury Villa") == "villa"
    assert normalize_room_tier(None) == "standard"
    assert normalize_room_tier("") == "standard"


def test_normalize_meal_plan():
    assert normalize_meal_plan("Free Breakfast") == "breakfast"
    assert normalize_meal_plan("Breakfast included") == "breakfast"
    assert normalize_meal_plan("Room Only") == "room_only"
    assert normalize_meal_plan("Half Board (Dinner included)") == "half_board"
    assert normalize_meal_plan("All Inclusive") == "all_inclusive"
    assert normalize_meal_plan(None) == "room_only"
    assert normalize_meal_plan("") == "room_only"


def test_cohort_key_and_comparability():
    offer_base = {
        "room_type": "Deluxe King Room",
        "max_occupancy": 2,
        "meal_plan": "Breakfast included",
        "cancellation_category": "free",
    }
    offer_matching = {
        "room_type": "Deluxe Twin Bed",
        "max_occupancy": 2,
        "meal_plan": "Free Breakfast",
        "cancellation_category": "free",
    }
    offer_diff_tier = {
        "room_type": "Executive Suite",
        "max_occupancy": 2,
        "meal_plan": "Free Breakfast",
        "cancellation_category": "free",
    }
    offer_diff_occupancy = {
        "room_type": "Deluxe King Room",
        "max_occupancy": 3,
        "meal_plan": "Free Breakfast",
        "cancellation_category": "free",
    }
    offer_diff_meal = {
        "room_type": "Deluxe King Room",
        "max_occupancy": 2,
        "meal_plan": "Room Only",
        "cancellation_category": "free",
    }
    offer_diff_cancel = {
        "room_type": "Deluxe King Room",
        "max_occupancy": 2,
        "meal_plan": "Breakfast included",
        "cancellation_category": "non_refundable",
    }

    assert cohort_key(offer_base) == ("deluxe", 2, "breakfast", "free")
    assert cohort_key(offer_matching) == ("deluxe", 2, "breakfast", "free")

    is_comp, reason = are_offers_comparable(offer_base, offer_matching)
    assert is_comp is True
    assert reason is None

    # Mismatches
    is_comp, reason = are_offers_comparable(offer_base, offer_diff_tier)
    assert is_comp is False
    assert "room tier mismatch (deluxe vs suite)" in reason

    is_comp, reason = are_offers_comparable(offer_base, offer_diff_occupancy)
    assert is_comp is False
    assert "occupancy mismatch (2 vs 3 guests)" in reason

    is_comp, reason = are_offers_comparable(offer_base, offer_diff_meal)
    assert is_comp is False
    assert "meal plan mismatch (breakfast vs room_only)" in reason

    is_comp, reason = are_offers_comparable(offer_base, offer_diff_cancel)
    assert is_comp is False
    assert "cancellation mismatch (free vs non_refundable)" in reason


def test_verification_level_model_validation():
    # Checkout verification level
    pr_checkout = ProbeResult(
        site="cleartrip",
        reached_payment_page=True,
        price_final_payable=5000.0,
        verification_level="checkout",
    )
    assert pr_checkout.verification_level == "checkout"

    # Listing verification level
    pr_listing = ProbeResult(
        site="agoda",
        reached_payment_page=False,
        price_shown_on_listing=4500.0,
        verification_level="listing",
    )
    assert pr_listing.verification_level == "listing"

    # Offer model with verification_level
    off = Offer(
        offer_id="test_off",
        hotel_id="h1",
        run_id="run_123",
        started_at="2026-11-20T10:00:00+05:30",
        finished_at="2026-11-20T10:00:20+05:30",
        steps=10,
        cost_usd=0.0,
        site="cleartrip",
        status="verified",
        reached_payment_page=True,
        furthest_step="payment",
        hotel_name="Test Hotel",
        hotel_url="https://www.cleartrip.com/hotels/details/123",
        price_final_payable=5000.0,
        currency="INR",
        verification_level="checkout",
    )
    assert off.verification_level == "checkout"


def test_cohort_comparison_with_fixtures():
    demo_run_path = Path("fixtures/demo_run.json")
    assert demo_run_path.exists()

    with open(demo_run_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    offers = data.get("offers", [])
    assert len(offers) > 0

    # Every offer should have verification_level specified
    for off in offers:
        assert off.get("verification_level") in ["checkout", "listing"]

    # Compare offers within the same hotel
    h1_offers = [o for o in offers if o.get("hotel_id") == "h1"]
    if len(h1_offers) >= 2:
        off_a, off_b = h1_offers[0], h1_offers[1]
        is_comp, reason = are_offers_comparable(off_a, off_b)
        warnings = non_comparable_warnings([off_a, off_b])
        if not is_comp:
            assert len(warnings) > 0
            assert "not comparable" in reason


def test_saved_cleartrip_html_analysis():
    html_path = Path("results/recon/cleartrip/after_book_click.html")
    if html_path.exists():
        content = html_path.read_text(encoding="utf-8", errors="ignore")
        assert len(content) > 100
        # HTML should contain pricing / hotel context
        assert "Radisson Blu" in content or "hotel" in content.lower() or "price" in content.lower()
