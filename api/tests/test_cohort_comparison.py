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


def test_la_marvella_saved_breakdown_and_payable():
    """Verify La Marvella breakdown from saved payment review page.
    Assures that Rs 15,639 is the undiscounted rack price, while final payable is Rs 11,604.
    """
    html_path = Path("results/recon/cleartrip/la_marvella_payment_page.html")
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")

    # 1. Total element extraction
    import re
    m_tot = re.search(r'>Total</h4>\s*<h2[^>]*>₹\s*([0-9,]+)', html)
    assert m_tot is not None
    payable = float(m_tot.group(1).replace(",", ""))
    assert payable == 11604.0  # Final amount on payment page, NOT 15639.0

    # 2. Line items extraction
    pairs = re.findall(r'flex-between[^>]*><p[^>]*>([^<]+)</p><p[^>]*>(-?₹\s*[0-9,]+)</p>', html)
    allowed = ['1 room x 1 night', 'hotel taxes', 'property discount', 'convenience fee', 'coupon discount']
    fee_lines = {}
    for lbl, amt_str in pairs:
        clean_lbl = lbl.strip()
        amt = float(amt_str.replace("₹", "").replace(",", ""))
        if 'penalty' not in clean_lbl.lower() and 'cancellation' not in clean_lbl.lower():
            if any(k in clean_lbl.lower() for k in allowed):
                fee_lines[clean_lbl] = amt

    # Check key figures
    assert fee_lines.get("1 room x 1 night") == 15639.0  # Raw room rate before discounts
    assert fee_lines.get("Property discount") == -4692.0
    assert fee_lines.get("Hotel taxes") == 1971.0
    assert fee_lines.get("Convenience fee") == 1095.0
    assert fee_lines.get("Coupon discount (CTHOTEL)") == -2408.0

    # Reconciliation
    lines_sum = sum(fee_lines.values())
    assert abs(lines_sum - payable) <= 1.0  # 11605 vs 11604


def test_cleartrip_dates_variability():
    """Verify Cleartrip date test results on same hotel across 3 dates."""
    dates_path = Path("results/cleartrip_dates_test.json")
    assert dates_path.exists()
    runs = json.loads(dates_path.read_text(encoding="utf-8"))
    assert len(runs) == 3

    p1 = runs[0]["max_price"]
    p2 = runs[1]["max_price"]
    p3 = runs[2]["max_price"]

    # Verify prices vary
    assert p1 != p2
    assert p2 != p3
    assert p1 == 10610.0
    assert p2 == 12418.0
    assert p3 == 18831.0

    # Verify screenshots exist
    for r in runs:
        assert Path(r["screenshot"]).exists()


def test_no_ranking_across_verification_levels():
    """Enforce invariant: Google Hotels is indicative-only and ranking across verification levels is rejected."""
    from api.services.scoring import validate_no_cross_level_ranking, rank_offers

    checkout_offer = {
        "offer_id": "off_ct",
        "hotel_id": "h1",
        "site": "Cleartrip",
        "status": "verified",
        "price_final_payable": 11077.0,
        "currency": "INR",
        "verification_level": "checkout",
        "meal_plan": "Room Only",
        "cancellation_category": "free",
    }
    listing_offer = {
        "offer_id": "off_gh",
        "hotel_id": "h1",
        "site": "Google Hotels",
        "status": "unverified",
        "price_shown_on_listing": 10500.0,
        "price_final_payable": None,
        "currency": "INR",
        "verification_level": "listing",
        "meal_plan": "Room Only",
        "cancellation_category": "free",
        "notes": "Indicative only",
    }

    # Attempting to validate or rank mixed levels must raise ValueError
    with pytest.raises(ValueError, match="Cross-.*ranking violation"):
        validate_no_cross_level_ranking([checkout_offer, listing_offer])

    with pytest.raises(ValueError, match="Cross-level ranking violation"):
        rank_offers([checkout_offer, listing_offer], {})

    # Ranking checkout-only offers succeeds
    ranked = rank_offers([checkout_offer], {})
    assert len(ranked) == 1
    assert ranked[0]["offer_id"] == "off_ct"


def test_payable_traceable_to_saved_page():
    """Fail if any verified offer has a payable that cannot be traced to saved evidence."""
    demo_run = Path("fixtures/demo_run.json")
    if demo_run.exists():
        data = json.loads(demo_run.read_text(encoding="utf-8"))
        for off in data.get("offers", []):
            if off.get("status") == "verified" and off.get("price_final_payable") is not None:
                payable = float(off["price_final_payable"])
                p_int = str(int(payable))
                # Traceable in payment_page_text, notes, or evidence
                texts = [
                    off.get("payment_page_text") or "",
                    off.get("listing_page_text") or "",
                    off.get("notes") or "",
                ]
                for ev in off.get("evidence", []):
                    if ev.get("extracted_value"):
                        texts.append(str(ev["extracted_value"]))
                combined = " ".join(texts)
                assert p_int in combined or str(payable) in combined, (
                    f"Payable {payable} for offer {off.get('offer_id')} is untraceable to saved evidence"
                )


def test_unsupported_platforms_marked_blocked():
    """Verify Treebo, FabHotels, and StayVista are recorded as blocked (login/otp/layout)."""
    bench_file = Path("results/benchmark_10runs_summary.json")
    if bench_file.exists():
        data = json.loads(bench_file.read_text(encoding="utf-8"))
        for t_run in data.get("treebo", []):
            assert t_run["success"] is False
            assert t_run["blocker"] in ["login", "otp", "layout"]
            assert t_run["payable"] is None
        for f_run in data.get("fabhotels", []):
            assert f_run["success"] is False
            assert f_run["blocker"] in ["login", "otp"]
            assert f_run["payable"] is None
        for s_run in data.get("stayvista", []):
            assert s_run["success"] is False
            assert s_run["blocker"] in ["layout", "other"]
            assert s_run["payable"] is None



