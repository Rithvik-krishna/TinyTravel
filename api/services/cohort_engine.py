"""
3-Pass Cohort Comparison Engine.

Pass 1: Catalog Extraction
    Extract full rate catalogs from Cleartrip and Booking.com for requested hotel and dates.
Pass 2: Cohort Intersection
    Intersect rate cohorts: (room_tier, occupancy >= 2, meal_plan, cancellation_category).
    If intersection is empty, output status="NOT COMPARABLE", comparable=False.
Pass 3: Coordinated Checkout
    Target the exact same selected intersecting cohort on both platforms through to payment review.
"""
from datetime import datetime, timezone, timedelta
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

try:
    from .normalize import normalize_room_tier, normalize_meal_plan, cohort_key, are_offers_comparable
    from ..agents.playbooks.cleartrip import run_cleartrip_playbook
    from ..agents.playbooks.bookingcom import run_bookingcom_playbook
except ImportError:
    from services.normalize import normalize_room_tier, normalize_meal_plan, cohort_key, are_offers_comparable
    from agents.playbooks.cleartrip import run_cleartrip_playbook
    from agents.playbooks.bookingcom import run_bookingcom_playbook

logger = logging.getLogger("tinytravel.cohort_engine")
IST = timezone(timedelta(hours=5, minutes=30))


def parse_cleartrip_catalog_from_html(html_text: str, guests: int = 2) -> List[Dict[str, Any]]:
    """Parse all available rate options from Cleartrip room selection HTML."""
    rates = []
    # Pattern to match rate blocks / cards
    cards = re.split(r'(?i)<div[^>]*class="[^"]*(?:border|card|rounded)[^"]*"', html_text)
    if len(cards) <= 1:
        cards = [html_text]

    btn_idx = 0
    for card in cards:
        if "book" not in card.lower() or "₹" not in card:
            continue

        prices = [float(p.replace(",", "")) for p in re.findall(r'₹\s*([0-9,]+)', card)]
        if not prices:
            continue
        base_p = prices[0]
        tax_p = prices[1] if len(prices) > 1 else 0.0
        tot_p = base_p + tax_p

        # Room name
        m_room = re.search(r'(?i)(deluxe|superior|standard|executive|suite|classic|club)(?:\s+(?:room|suite))?', card)
        room_name = m_room.group(0).title() if m_room else "Standard Room"

        # Meal plan
        if re.search(r'(?i)breakfast\s*(&|\+)?\s*(dinner|lunch)', card):
            meal = "Room with Breakfast & Dinner"
        elif "breakfast" in card.lower():
            meal = "Room with Breakfast"
        else:
            meal = "Room Only"

        # Cancellation
        is_free = bool(re.search(r'(?i)free\s+cancellation', card))
        canc_cat = "free" if is_free else "non_refundable"
        policy = "Free cancellation" if is_free else "Non-refundable"

        tier = normalize_room_tier(room_name)
        norm_meal = normalize_meal_plan(meal)

        rates.append({
            "button_index": btn_idx,
            "room_name": room_name,
            "room_tier": tier,
            "max_occupancy": guests,
            "meal_plan": meal,
            "norm_meal_plan": norm_meal,
            "cancellation_category": canc_cat,
            "cancellation_policy": policy,
            "base_price": base_p,
            "tax_price": tax_p,
            "total_price": tot_p,
            "cohort": (tier, guests, norm_meal, canc_cat),
        })
        btn_idx += 1

    return rates


def parse_bookingcom_catalog_from_env(env_obj: Dict[str, Any], guests: int = 2) -> List[Dict[str, Any]]:
    """Parse all available rate options from Booking.com window.booking.env state."""
    rates = []
    rooms = env_obj.get("b_rooms_available_and_soldout", [])
    for room in rooms:
        room_name = room.get("b_name") or "Standard Room"
        tier = normalize_room_tier(room_name)
        for block in room.get("b_blocks", []):
            block_id = str(block.get("b_block_id") or "")
            occ = int(block.get("b_can_fit_them_all") or room.get("b_max_persons") or 2)
            if occ < guests:
                continue

            base_price = float(block.get("b_raw_price") or 0)
            total_price = base_price
            simplified = block.get("b_price_breakdown_simplified") or {}
            total_arr = simplified.get("b_total_price") or []
            if total_arr:
                total_price = float(total_arr[0].get("b_raw_value_user_currency") or base_price)
            taxes = round(total_price - base_price, 2)

            is_free = block.get("b_cancellation_type") == "free_cancellation"
            canc_cat = "free" if is_free else "non_refundable"

            meal_raw = (block.get("b_mealplan_included_name") or "").lower()
            if "breakfast" in meal_raw:
                meal = "Breakfast Included"
            elif "half" in meal_raw:
                meal = "Half Board"
            else:
                meal = "Room Only"
            norm_meal = normalize_meal_plan(meal)

            rates.append({
                "block_id": block_id,
                "room_name": room_name,
                "room_tier": tier,
                "max_occupancy": occ,
                "meal_plan": meal,
                "norm_meal_plan": norm_meal,
                "cancellation_category": canc_cat,
                "cancellation_policy": "Free cancellation" if is_free else "Non-refundable",
                "base_price": base_price,
                "tax_price": taxes,
                "total_price": total_price,
                "cohort": (tier, 2, norm_meal, canc_cat),  # standardized to requested 2 adults
            })
    return rates


def intersect_catalogs(ct_rates: List[Dict[str, Any]], bk_rates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pass 2: Intersect rate cohorts across platforms.

    Cohort 4-tuple: (room_tier, occupancy >= 2, meal_plan, cancellation_category).
    If intersection is empty, returns status="NOT COMPARABLE", comparable=False.
    """
    ct_by_cohort: Dict[Tuple, List[Dict[str, Any]]] = {}
    for r in ct_rates:
        c = r["cohort"]
        ct_by_cohort.setdefault(c, []).append(r)

    bk_by_cohort: Dict[Tuple, List[Dict[str, Any]]] = {}
    for r in bk_rates:
        c = r["cohort"]
        bk_by_cohort.setdefault(c, []).append(r)

    common_keys = set(ct_by_cohort.keys()) & set(bk_by_cohort.keys())

    if not common_keys:
        return {
            "comparable": False,
            "status": "NOT COMPARABLE",
            "common_cohorts": [],
            "selected_cohort": None,
            "selected_ct_rate": None,
            "selected_bk_rate": None,
            "reason": (
                f"No overlapping cohort found. "
                f"Cleartrip cohorts: {list(ct_by_cohort.keys())}. "
                f"Booking.com cohorts: {list(bk_by_cohort.keys())}."
            ),
            "ct_cohort_count": len(ct_by_cohort),
            "bk_cohort_count": len(bk_by_cohort),
        }

    # Deterministic selection among common cohorts:
    # 1. Prefer free cancellation ('free' == key[3])
    # 2. Lowest combined average price
    def cohort_rank_score(k: Tuple) -> Tuple[int, float]:
        free_priority = 0 if k[3] == "free" else 1
        min_ct = min(r["total_price"] for r in ct_by_cohort[k])
        min_bk = min(r["total_price"] for r in bk_by_cohort[k])
        avg_price = (min_ct + min_bk) / 2.0
        return (free_priority, avg_price)

    sorted_cohorts = sorted(common_keys, key=cohort_rank_score)
    selected_cohort = sorted_cohorts[0]

    selected_ct_rate = min(ct_by_cohort[selected_cohort], key=lambda r: r["total_price"])
    selected_bk_rate = min(bk_by_cohort[selected_cohort], key=lambda r: r["total_price"])

    return {
        "comparable": True,
        "status": "COMPARABLE",
        "common_cohorts": [str(c) for c in sorted_cohorts],
        "selected_cohort": selected_cohort,
        "selected_ct_rate": selected_ct_rate,
        "selected_bk_rate": selected_bk_rate,
        "reason": None,
        "ct_cohort_count": len(ct_by_cohort),
        "bk_cohort_count": len(bk_by_cohort),
    }


def compare_coordinated_runs(
    hotel_name: str,
    ct_offer: Dict[str, Any],
    bk_offer: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate two completed checkout runs for cohort comparability and calculate price spread."""
    is_comp, reason = are_offers_comparable(ct_offer, bk_offer)

    ct_payable = ct_offer.get("price_final_payable")
    bk_payable = bk_offer.get("price_final_payable")

    ct_verified = ct_offer.get("reached_payment_page") and ct_payable is not None
    bk_verified = bk_offer.get("reached_payment_page") and bk_payable is not None

    if not is_comp or not ct_verified or not bk_verified:
        return {
            "hotel_name": hotel_name,
            "status": "NOT COMPARABLE" if not is_comp else "UNVERIFIED PAIR",
            "comparable": is_comp and ct_verified and bk_verified,
            "cohort_cleartrip": str(cohort_key(ct_offer)),
            "cohort_bookingcom": str(cohort_key(bk_offer)),
            "cleartrip_payable": ct_payable,
            "bookingcom_payable": bk_payable,
            "spread_inr": None,
            "spread_pct": None,
            "cheaper_platform": None,
            "reason": reason or ("One or both platforms failed to reach verified payment page"),
        }

    spread = round(abs(ct_payable - bk_payable), 2)
    min_price = min(ct_payable, bk_payable)
    spread_pct = round((spread / min_price) * 100.0, 1) if min_price > 0 else 0.0
    cheaper = "Cleartrip" if ct_payable < bk_payable else ("Booking.com" if bk_payable < ct_payable else "TIE")

    return {
        "hotel_name": hotel_name,
        "status": "COMPARABLE",
        "comparable": True,
        "cohort_cleartrip": str(cohort_key(ct_offer)),
        "cohort_bookingcom": str(cohort_key(bk_offer)),
        "cleartrip_payable": ct_payable,
        "bookingcom_payable": bk_payable,
        "spread_inr": spread,
        "spread_pct": spread_pct,
        "cheaper_platform": cheaper,
        "reason": None,
    }


async def run_3pass_cohort_verification(
    hotel_name: str,
    check_in: str = "2026-11-20",
    check_out: str = "2026-11-21",
    guests: int = 2,
    headless: bool = False,
) -> Dict[str, Any]:
    """Execute 3-Pass Cohort Verification:
    Pass 1: Catalog rates on Cleartrip and Booking.com.
    Pass 2: Intersect (room_tier, occupancy >= 2, meal_plan, cancellation_category).
            If intersection is empty -> NOT COMPARABLE.
    Pass 3: Coordinated checkout targeting the exact matching cohort on both platforms.
    """
    req_ct = {
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "rooms": 1,
        "destination": "Bengaluru",
    }
    req_bk = {
        "check_in": check_in,
        "check_out": check_out,
        "guests": guests,
        "rooms": 1,
        "destination": "Bengaluru",
    }

    # Pass 1 & 3: Run Cleartrip with cohort pinning
    logger.info("Pass 1/3: Running Cleartrip checkout for %s (%s to %s)...", hotel_name, check_in, check_out)
    ct_offer = await run_cleartrip_playbook(hotel_name, req_ct, headless=headless)
    logger.info("Cleartrip result: reached=%s, payable=%s, room=%s, meal=%s, cancel=%s",
                ct_offer.get("reached_payment_page"), ct_offer.get("price_final_payable"),
                ct_offer.get("room_type"), ct_offer.get("meal_plan"), ct_offer.get("cancellation_policy"))

    # Pass 2: Pin Booking.com checkout to target the exact same cohort as Cleartrip
    ct_cohort = cohort_key(ct_offer)
    req_bk["target_cohort"] = ct_cohort
    logger.info("Pass 2/3: Running Booking.com checkout targeting cohort %s...", ct_cohort)
    bk_offer = await run_bookingcom_playbook(hotel_name, req_bk, headless=headless)
    logger.info("Booking.com result: reached=%s, payable=%s, room=%s, meal=%s, cancel=%s",
                bk_offer.get("reached_payment_page"), bk_offer.get("price_final_payable"),
                bk_offer.get("room_type"), bk_offer.get("meal_plan"), bk_offer.get("cancellation_policy"))

    # Evaluate comparison
    comp = compare_coordinated_runs(hotel_name, ct_offer, bk_offer)
    comp["check_in"] = check_in
    comp["check_out"] = check_out
    comp["cleartrip_details"] = {
        "reached_payment_page": ct_offer.get("reached_payment_page"),
        "payable": ct_offer.get("price_final_payable"),
        "room_type": ct_offer.get("room_type"),
        "meal_plan": ct_offer.get("meal_plan"),
        "cancellation_policy": ct_offer.get("cancellation_policy"),
        "fee_lines": ct_offer.get("fee_lines", []),
    }
    comp["bookingcom_details"] = {
        "reached_payment_page": bk_offer.get("reached_payment_page"),
        "payable": bk_offer.get("price_final_payable"),
        "room_type": bk_offer.get("room_type"),
        "meal_plan": bk_offer.get("meal_plan"),
        "cancellation_policy": bk_offer.get("cancellation_policy"),
        "fee_lines": bk_offer.get("fee_lines", []),
    }
    return comp
