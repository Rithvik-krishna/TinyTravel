"""
Unit tests for the 3-Pass Cohort Comparison Engine.
Validates:
1. Pass 1: Catalog parsing from Cleartrip HTML and Booking.com env.
2. Pass 2: Cohort intersection with non-empty intersection returning COMPARABLE,
   and disjoint cohorts returning NOT COMPARABLE.
3. Pass 3: Coordinated run comparability and spread calculation.
"""
import pytest
from api.services.cohort_engine import (
    parse_cleartrip_catalog_from_html,
    parse_bookingcom_catalog_from_env,
    intersect_catalogs,
    compare_coordinated_runs,
)


def test_cleartrip_catalog_parsing():
    mock_html = """
    <div class="card p-4">
        <h4>Deluxe Room</h4>
        <p>Room with Breakfast · Free cancellation</p>
        <span>₹ 8,429</span>
        <span>+ ₹ 1,517 taxes & fees</span>
        <button>Book Now</button>
    </div>
    <div class="card p-4">
        <h4>Executive Suite</h4>
        <p>Room Only · Non-refundable</p>
        <span>₹ 14,200</span>
        <span>+ ₹ 2,556 taxes & fees</span>
        <button>Book</button>
    </div>
    """
    rates = parse_cleartrip_catalog_from_html(mock_html, guests=2)
    assert len(rates) == 2
    assert rates[0]["room_tier"] == "deluxe"
    assert rates[0]["norm_meal_plan"] == "breakfast"
    assert rates[0]["cancellation_category"] == "free"
    assert rates[0]["total_price"] == 8429.0 + 1517.0
    assert rates[0]["cohort"] == ("deluxe", 2, "breakfast", "free")

    assert rates[1]["room_tier"] == "suite"
    assert rates[1]["norm_meal_plan"] == "room_only"
    assert rates[1]["cancellation_category"] == "non_refundable"


def test_bookingcom_catalog_parsing():
    mock_env = {
        "b_has_available_rooms": True,
        "b_rooms_available_and_soldout": [
            {
                "b_name": "Deluxe King Room",
                "b_max_persons": 2,
                "b_blocks": [
                    {
                        "b_block_id": "blk_101",
                        "b_can_fit_them_all": 2,
                        "b_raw_price": "8100.00",
                        "b_mealplan_included_name": "breakfast",
                        "b_cancellation_type": "free_cancellation",
                        "b_price_breakdown_simplified": {
                            "b_total_price": [{"b_raw_value_user_currency": "9558.00"}]
                        },
                    },
                    {
                        "b_block_id": "blk_102",
                        "b_can_fit_them_all": 2,
                        "b_raw_price": "7200.00",
                        "b_mealplan_included_name": "room_only",
                        "b_cancellation_type": "non_refundable",
                        "b_price_breakdown_simplified": {
                            "b_total_price": [{"b_raw_value_user_currency": "8496.00"}]
                        },
                    },
                ],
            }
        ]
    }
    rates = parse_bookingcom_catalog_from_env(mock_env, guests=2)
    assert len(rates) == 2
    assert rates[0]["block_id"] == "blk_101"
    assert rates[0]["room_tier"] == "deluxe"
    assert rates[0]["norm_meal_plan"] == "breakfast"
    assert rates[0]["cancellation_category"] == "free"
    assert rates[0]["total_price"] == 9558.0
    assert rates[0]["cohort"] == ("deluxe", 2, "breakfast", "free")


def test_intersect_catalogs_matching():
    ct_rates = [
        {
            "button_index": 0,
            "room_name": "Deluxe Room",
            "room_tier": "deluxe",
            "max_occupancy": 2,
            "norm_meal_plan": "breakfast",
            "cancellation_category": "free",
            "total_price": 9946.0,
            "cohort": ("deluxe", 2, "breakfast", "free"),
        },
        {
            "button_index": 1,
            "room_name": "Standard Room",
            "room_tier": "standard",
            "max_occupancy": 2,
            "norm_meal_plan": "room_only",
            "cancellation_category": "non_refundable",
            "total_price": 6000.0,
            "cohort": ("standard", 2, "room_only", "non_refundable"),
        },
    ]

    bk_rates = [
        {
            "block_id": "blk_deluxe_free",
            "room_name": "Deluxe Room",
            "room_tier": "deluxe",
            "max_occupancy": 2,
            "norm_meal_plan": "breakfast",
            "cancellation_category": "free",
            "total_price": 9558.0,
            "cohort": ("deluxe", 2, "breakfast", "free"),
        },
        {
            "block_id": "blk_suite",
            "room_name": "Presidential Suite",
            "room_tier": "suite",
            "max_occupancy": 2,
            "norm_meal_plan": "breakfast",
            "cancellation_category": "free",
            "total_price": 25000.0,
            "cohort": ("suite", 2, "breakfast", "free"),
        },
    ]

    res = intersect_catalogs(ct_rates, bk_rates)
    assert res["comparable"] is True
    assert res["status"] == "COMPARABLE"
    assert res["selected_cohort"] == ("deluxe", 2, "breakfast", "free")
    assert res["selected_ct_rate"]["button_index"] == 0
    assert res["selected_bk_rate"]["block_id"] == "blk_deluxe_free"


def test_intersect_catalogs_empty_disjoint():
    ct_rates = [
        {
            "button_index": 0,
            "room_name": "Executive Suite",
            "room_tier": "suite",
            "max_occupancy": 2,
            "norm_meal_plan": "breakfast",
            "cancellation_category": "free",
            "total_price": 28000.0,
            "cohort": ("suite", 2, "breakfast", "free"),
        }
    ]

    bk_rates = [
        {
            "block_id": "blk_standard_ro",
            "room_name": "Standard Room",
            "room_tier": "standard",
            "max_occupancy": 2,
            "norm_meal_plan": "room_only",
            "cancellation_category": "non_refundable",
            "total_price": 4500.0,
            "cohort": ("standard", 2, "room_only", "non_refundable"),
        }
    ]

    res = intersect_catalogs(ct_rates, bk_rates)
    assert res["comparable"] is False
    assert res["status"] == "NOT COMPARABLE"
    assert "No overlapping cohort" in res["reason"]
    assert res["selected_cohort"] is None


def test_compare_coordinated_runs_matched():
    ct_offer = {
        "room_type": "Deluxe King Room",
        "max_occupancy": 2,
        "meal_plan": "Room with Breakfast",
        "cancellation_category": "free",
        "reached_payment_page": True,
        "price_final_payable": 9946.0,
    }
    bk_offer = {
        "room_type": "Deluxe Room",
        "max_occupancy": 2,
        "meal_plan": "Breakfast Included",
        "cancellation_category": "free",
        "reached_payment_page": True,
        "price_final_payable": 9558.0,
    }

    res = compare_coordinated_runs("Radisson Blu Atria Bengaluru", ct_offer, bk_offer)
    assert res["comparable"] is True
    assert res["status"] == "COMPARABLE"
    assert res["spread_inr"] == 388.0
    assert res["spread_pct"] == 4.1
    assert res["cheaper_platform"] == "Booking.com"


def test_compare_coordinated_runs_unmatched():
    ct_offer = {
        "room_type": "Superior Room",
        "max_occupancy": 2,
        "meal_plan": "Room Only",
        "cancellation_category": "non_refundable",
        "reached_payment_page": True,
        "price_final_payable": 7611.0,
    }
    bk_offer = {
        "room_type": "Executive Suite",
        "max_occupancy": 2,
        "meal_plan": "Breakfast Included",
        "cancellation_category": "free",
        "reached_payment_page": True,
        "price_final_payable": 32265.0,
    }

@pytest.mark.anyio
async def test_cohort_engine_stops_before_checkout_when_intersection_empty():
    """Verify that if cohort intersection is empty, execution stops before checkout.
    
    No checkout playbook is called; returns status='NOT COMPARABLE' with stopped_before_checkout=True.
    """
    from api.services.cohort_engine import run_3pass_cohort_verification

    # Disjoint catalogs: Cleartrip only has standard, Booking.com only has suite
    ct_rates = [
        {
            "button_index": 0,
            "room_name": "Standard Room Only",
            "room_tier": "standard",
            "max_occupancy": 2,
            "norm_meal_plan": "room_only",
            "cancellation_category": "free",
            "total_price": 5000.0,
            "cohort": ("standard", 2, "room_only", "free"),
        }
    ]
    bk_rates = [
        {
            "block_id": "blk_presidential",
            "room_name": "Presidential Suite",
            "room_tier": "suite",
            "max_occupancy": 2,
            "norm_meal_plan": "breakfast",
            "cancellation_category": "free",
            "total_price": 35000.0,
            "cohort": ("suite", 2, "breakfast", "free"),
        }
    ]

    res = await run_3pass_cohort_verification(
        hotel_name="Radisson Blu Atria Bengaluru",
        check_in="2026-11-20",
        check_out="2026-11-21",
        guests=2,
        headless=True,
        ct_rates=ct_rates,
        bk_rates=bk_rates,
    )

    assert res["comparable"] is False
    assert res["status"] == "NOT COMPARABLE"
    assert res["stopped_before_checkout"] is True
    assert res["cleartrip_payable"] is None
    assert res["bookingcom_payable"] is None
    assert res["spread_inr"] is None
    assert "No overlapping cohort found" in res["reason"]

