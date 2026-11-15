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
    assert normalize_room_tier("Standard Dorm 6-bed") == "dorm"
    assert normalize_room_tier("1 Bed in 8-bed Mixed Dormitory") == "dorm"
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


def test_passing_platforms_fixture_validation():
    fixture_path = Path("fixtures/passing_platforms_offers.json")
    assert fixture_path.exists()

    with open(fixture_path, "r", encoding="utf-8") as f:
        raw_offers = json.load(f)

    assert len(raw_offers) == 10
    checkout_sites = {"cleartrip", "booking.com", "Treebo Hotels", "FabHotels", "StayVista"}
    listing_sites = {"Google Hotels", "Trip.com", "Hostelworld", "OneFineRate", "Agoda"}

    for raw in raw_offers:
        # Validate Pydantic model
        offer = Offer.model_validate(raw)
        if offer.site in checkout_sites:
            assert offer.verification_level == "checkout"
            assert offer.reached_payment_page is True
            assert offer.price_final_payable is not None
        elif offer.site in listing_sites:
            assert offer.verification_level == "listing"
            assert offer.reached_payment_page is False
            assert offer.price_shown_on_listing is not None


def test_cross_platform_cohort_comparison():
    fixture_path = Path("fixtures/passing_platforms_offers.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        offers = {o["site"]: o for o in json.load(f)}

    # 1. Matching Cohort: Booking.com vs Treebo Hotels on Treebo Tiba
    # Both are Standard Double Room, 2 guests, Room Only, non_refundable
    treebo_off = offers["Treebo Hotels"]
    booking_off = offers["booking.com"]
    is_comp, reason = are_offers_comparable(treebo_off, booking_off)
    assert is_comp is True
    assert reason is None
    assert cohort_key(treebo_off) == ("standard", 2, "room_only", "non_refundable")
    assert cohort_key(booking_off) == ("standard", 2, "room_only", "non_refundable")

    # 2. Mismatched Room Tier & Cancellation: Treebo (Standard Non-ref) vs Cleartrip (Deluxe Free)
    cleartrip_off = offers["cleartrip"]
    is_comp, reason = are_offers_comparable(treebo_off, cleartrip_off)
    assert is_comp is False
    assert "not comparable" in reason
    assert "room tier mismatch (standard vs deluxe)" in reason
    assert "cancellation mismatch (non_refundable vs free)" in reason

    # 3. Hostels Cohort: Hostelworld Dorm (1 guest, dorm) vs Treebo Standard (2 guests, standard)
    hostel_off = offers["Hostelworld"]
    is_comp, reason = are_offers_comparable(hostel_off, treebo_off)
    assert is_comp is False
    assert "room tier mismatch (dorm vs standard)" in reason
    assert "occupancy mismatch (1 vs 2 guests)" in reason

    # 4. Villas/Homestays Cohort: StayVista Villa (4 guests, villa) vs Cleartrip Deluxe (2 guests, deluxe)
    vista_off = offers["StayVista"]
    is_comp, reason = are_offers_comparable(vista_off, cleartrip_off)
    assert is_comp is False
    assert "room tier mismatch (villa vs deluxe)" in reason
    assert "occupancy mismatch (4 vs 2 guests)" in reason


def test_saved_recon_results_exist():
    # Verify all generated recon datasets are present and non-empty
    direct_path = Path("results/recon_direct_otas.json")
    assert direct_path.exists()
    direct_data = json.loads(direct_path.read_text(encoding="utf-8"))
    assert "expedia" in direct_data
    assert "tripcom" in direct_data
    assert "onefinerate" in direct_data

    brands_path = Path("results/recon_brands_and_homestays.json")
    assert brands_path.exists()
    brands_data = json.loads(brands_path.read_text(encoding="utf-8"))
    assert "treebo" in brands_data
    assert "fabhotels" in brands_data
    assert "stayvista" in brands_data
    assert "hostelworld" in brands_data

    meta_path = Path("results/recon_metasearch.json")
    assert meta_path.exists()
    meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "googlehotels" in meta_data
    assert "trivago" in meta_data
    assert "kayak" in meta_data

    docker_path = Path("results/docker_passing_sites_test.json")
    assert docker_path.exists()
    docker_data = json.loads(docker_path.read_text(encoding="utf-8"))
    assert len(docker_data["results"]) >= 3

