"""Golden tests verifying that price engine reproduces fixtures/demo_run.json exactly.
Also tests edge cases (no verified offers, single verified, missing rating, all non-refundable).
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.scoring import (
    fee_leak_pct,
    reconciles,
    verified,
    transparency_score,
    rank_offers,
    pick_verdicts,
    summary_strip,
    non_comparable_warnings,
)
from services.dedupe import name_confidence, match_status

demo = json.loads((Path(__file__).parents[2] / "fixtures/demo_run.json").read_text(encoding="utf-8"))
rechecks_map = {r["offer_id"]: r for r in demo.get("rechecks", [])}


def test_fee_leak_matches_fixture():
    for o in demo["offers"]:
        assert fee_leak_pct(o["price_shown_on_listing"], o["price_final_payable"]) == o["fee_leak_pct"]


def test_verified_offers_reconcile_and_have_evidence():
    for o in demo["offers"]:
        assert bool(verified(o)) == (o["status"] == "verified"), o["offer_id"]


def test_real_cleartrip_numbers():
    o = next(x for x in demo["offers"] if x["offer_id"] == "h1_cleartrip")
    assert o["price_final_payable"] == 11276 and o["fee_leak_pct"] == 37.3
    assert reconciles(o["fee_lines"], 11276)


def test_dedupe_thresholds():
    assert match_status(name_confidence("La Marvella", "La Marvella")) == "merged"
    assert match_status(name_confidence("Urban Nest Inn", "Urban Nest Inn & Suites")) in ("suggested", "merged")


def test_transparency_score_matches_fixture():
    for o in demo["offers"]:
        recheck = rechecks_map.get(o["offer_id"])
        computed = transparency_score(o, recheck=recheck)
        expected = o["transparency"]
        assert computed["score"] == expected["score"], f"{o['offer_id']} score mismatch: {computed} vs {expected}"
        assert computed["note"] == expected["note"], f"{o['offer_id']} note mismatch: {computed} vs {expected}"
        if expected["breakdown"] is None:
            assert computed["breakdown"] is None
        else:
            assert computed["breakdown"] == expected["breakdown"], (
                f"{o['offer_id']} breakdown mismatch: {computed['breakdown']} vs {expected['breakdown']}"
            )


def test_ranking_matches_fixture():
    deal_mode = demo["verdicts"]["deal_mode"]
    computed_ranking = rank_offers(demo["offers"], demo["hotels"], deal_mode=deal_mode)
    expected_ranking = demo["verdicts"]["ranking"]

    assert len(computed_ranking) == len(expected_ranking)

    for comp, exp in zip(computed_ranking, expected_ranking):
        assert comp["offer_id"] == exp["offer_id"], f"Rank order mismatch: {comp['offer_id']} != {exp['offer_id']}"
        assert comp["total"] == exp["total"], f"{comp['offer_id']} total mismatch: {comp['total']} != {exp['total']}"
        assert comp["components"] == exp["components"], (
            f"{comp['offer_id']} components mismatch: {comp['components']} != {exp['components']}"
        )
        assert comp["weights"] == exp["weights"], (
            f"{comp['offer_id']} weights mismatch: {comp['weights']} != {exp['weights']}"
        )


def test_verdicts_matches_fixture():
    ranking = demo["verdicts"]["ranking"]
    computed = pick_verdicts(demo["offers"], ranking)

    # Check overall
    expected_overall = demo["verdicts"]["overall"]
    assert computed["overall"]["cheapest_verified"] == expected_overall["cheapest_verified"]
    assert computed["overall"]["safe_cheapest"] == expected_overall["safe_cheapest"]
    assert computed["overall"]["best_for_you"] == expected_overall["best_for_you"]
    assert computed["overall"]["headlines"] == expected_overall["headlines"]

    # Check per_hotel
    expected_per_hotel = demo["verdicts"]["per_hotel"]
    for hid, exp_h in expected_per_hotel.items():
        comp_h = computed["per_hotel"][hid]
        assert comp_h["cheapest_verified"] == exp_h["cheapest_verified"]
        assert comp_h["safe_cheapest"] == exp_h["safe_cheapest"]
        assert comp_h["best_for_you"] == exp_h["best_for_you"]
        assert comp_h["headlines"] == exp_h["headlines"]


def test_summary_strip_matches_fixture():
    # Calling summary_strip with the discovery count (24) reproduces demo_run.json summary_strip exactly
    summary = summary_strip(demo["offers"], demo["summary_strip"]["listings_found"])
    assert summary == demo["summary_strip"]

    # Calling with demo["listings"] reproduces all metrics with listings_found=len(listings)
    summary_from_listings = summary_strip(demo["offers"], demo["listings"])
    assert summary_from_listings["unique_hotels"] == demo["summary_strip"]["unique_hotels"]
    assert summary_from_listings["verified"] == demo["summary_strip"]["verified"]
    assert summary_from_listings["unverified"] == demo["summary_strip"]["unverified"]
    assert summary_from_listings["blocked"] == demo["summary_strip"]["blocked"]
    assert summary_from_listings["avg_fee_leak_pct"] == demo["summary_strip"]["avg_fee_leak_pct"]
    assert summary_from_listings["listings_found"] == len(demo["listings"])  # 8 candidate listings


def test_non_comparable_warnings_matches_fixture():
    warnings = non_comparable_warnings(demo["offers"])
    expected_warnings = demo["verdicts"]["non_comparable_warnings"]

    assert len(warnings) == len(expected_warnings)
    for comp, exp in zip(warnings, expected_warnings):
        assert comp["hotel_id"] == exp["hotel_id"]
        assert comp["offer_id"] == exp["offer_id"]
        assert comp["message"] == exp["message"]


# --- Edge Case Tests ---

def test_edge_no_verified_offers():
    unverified_offers = [
        {"offer_id": "off_1", "status": "unverified", "hotel_id": "h1"},
        {"offer_id": "off_2", "status": "blocked", "hotel_id": "h1"},
    ]
    hotels = [{"hotel_id": "h1", "rating": 4.0}]

    ranked = rank_offers(unverified_offers, hotels)
    assert ranked == []

    verdicts = pick_verdicts(unverified_offers, ranked)
    assert verdicts["overall"]["cheapest_verified"] is None
    assert verdicts["overall"]["safe_cheapest"] is None
    assert verdicts["overall"]["best_for_you"] is None

    strip = summary_strip(unverified_offers, listings=10)
    assert strip["verified"] == 0
    assert strip["unverified"] == 1
    assert strip["blocked"] == 1
    assert strip["avg_fee_leak_pct"] is None

    warns = non_comparable_warnings(unverified_offers)
    assert warns == []


def test_edge_single_verified_offer():
    single_offer = [
        {
            "offer_id": "off_solo",
            "hotel_id": "h1",
            "status": "verified",
            "site": "Agoda",
            "hotel_name": "Solo Hotel",
            "price_shown_on_listing": 5000.0,
            "price_final_payable": 6000.0,
            "cancellation_category": "free",
            "meal_plan": "Breakfast included",
            "currency": "INR",
            "fee_leak_pct": 20.0,
            "evidence": [
                {"step": "listing"},
                {"step": "room"},
                {"step": "payment"},
            ],
        }
    ]
    hotels = [{"hotel_id": "h1", "rating": 4.5}]

    ranked = rank_offers(single_offer, hotels, deal_mode="best_value")
    assert len(ranked) == 1
    assert ranked[0]["offer_id"] == "off_solo"
    assert ranked[0]["components"]["price"] == 100.0

    verdicts = pick_verdicts(single_offer, ranked)
    assert verdicts["overall"]["cheapest_verified"] == "off_solo"
    assert verdicts["overall"]["safe_cheapest"] == "off_solo"
    assert verdicts["overall"]["best_for_you"] == "off_solo"

    warns = non_comparable_warnings(single_offer)
    assert warns == []


def test_edge_missing_rating():
    offer = [
        {
            "offer_id": "off_no_rating",
            "hotel_id": "h_none",
            "status": "verified",
            "site": "Cleartrip",
            "hotel_name": "Unrated Inn",
            "price_shown_on_listing": 4000.0,
            "price_final_payable": 4000.0,
            "cancellation_category": "free",
            "meal_plan": "Breakfast included",
            "currency": "INR",
            "fee_leak_pct": 0.0,
            "evidence": [{"step": "listing"}, {"step": "room"}, {"step": "payment"}],
        }
    ]
    hotels = [{"hotel_id": "h_none", "rating": None}]

    ranked = rank_offers(offer, hotels, deal_mode="best_value")
    assert len(ranked) == 1
    # Quality must be None, and total should be 100.0 because price=100, prefs=100, canc=100, trans=100
    assert ranked[0]["components"]["quality"] is None
    assert ranked[0]["total"] == 100.0


def test_edge_all_non_refundable():
    non_ref_offers = [
        {
            "offer_id": "off_nr1",
            "hotel_id": "h1",
            "status": "verified",
            "site": "PlatformA",
            "hotel_name": "NR Hotel",
            "price_shown_on_listing": 8000.0,
            "price_final_payable": 9000.0,
            "cancellation_category": "non_refundable",
            "meal_plan": "Room only",
            "currency": "INR",
            "fee_leak_pct": 12.5,
            "evidence": [{"step": "listing"}, {"step": "room"}, {"step": "payment"}],
        },
        {
            "offer_id": "off_nr2",
            "hotel_id": "h1",
            "status": "verified",
            "site": "PlatformB",
            "hotel_name": "NR Hotel",
            "price_shown_on_listing": 8500.0,
            "price_final_payable": 9500.0,
            "cancellation_category": "non_refundable",
            "meal_plan": "Room only",
            "currency": "INR",
            "fee_leak_pct": 11.8,
            "evidence": [{"step": "listing"}, {"step": "room"}, {"step": "payment"}],
        },
    ]
    hotels = [{"hotel_id": "h1", "rating": 4.0}]

    ranked = rank_offers(non_ref_offers, hotels)
    verdicts = pick_verdicts(non_ref_offers, ranked)

    assert verdicts["overall"]["cheapest_verified"] == "off_nr1"
    # Safe cheapest MUST be null, not a wrong pick
    assert verdicts["overall"]["safe_cheapest"] is None
    assert verdicts["overall"]["best_for_you"] == "off_nr1"
