"""Pure scoring, verification, and price engine functions.
Golden-tested against fixtures/demo_run.json.
"""
from collections import Counter
from typing import Optional, Literal, Union

Status = Literal["verified", "unverified", "blocked"]
CancelCategory = Literal["free", "partial", "non_refundable"]
Reconciliation = Literal["ok", "mismatch"]

DEAL_MODE_WEIGHTS = {
    "lowest_price": {"price": 60, "prefs": 15, "cancellation": 15, "quality": 0, "transparency": 10},
    "best_value": {"price": 35, "prefs": 25, "cancellation": 20, "quality": 10, "transparency": 10},
    "most_transparent": {"price": 25, "prefs": 15, "cancellation": 15, "quality": 0, "transparency": 45},
}


def fee_leak_pct(
    listing: Optional[float],
    final: Optional[float],
    same_room: bool = True,
) -> Optional[float]:
    """Calculate fee leak percentage between listing price and final payable price.
    
    Label: "observed on this run".
    Formula: round((final - listing) / listing * 100, 1).
    Never compute fee_leak_pct from a different room (returns None if not same_room or listing is None).
    """
    if not same_room or not listing or final is None:
        return None
    return round((final - listing) / listing * 100, 1)


def reconciles(
    fee_lines: Optional[list[dict]],
    final: Optional[float],
    tol: float = 0.01,
    pay_now: Optional[float] = None,
    pay_at_hotel: Optional[float] = None,
) -> bool:
    """Check if itemized fee lines OR split payments (pay_now + pay_at_hotel) sum to final payable price within tolerance."""
    if final is None:
        return False
    # Check split payment match first
    if pay_now is not None and pay_at_hotel is not None:
        if abs((pay_now + pay_at_hotel) - final) <= tol * final:
            return True
    if not fee_lines:
        return False
    return abs(sum(l["amount"] for l in fee_lines) - final) <= tol * final


def reconciliation_status(
    fee_lines: Optional[list[dict]],
    final: Optional[float],
    tol: float = 0.01,
    pay_now: Optional[float] = None,
    pay_at_hotel: Optional[float] = None,
) -> Optional[Reconciliation]:
    """Return 'ok', 'mismatch', or None if fee lines / final price are absent."""
    if final is None:
        return None
    if not fee_lines and pay_now is None and pay_at_hotel is None:
        return None
    if reconciles(fee_lines, final, tol=tol, pay_now=pay_now, pay_at_hotel=pay_at_hotel):
        return "ok"
    return "mismatch"


def cancellation_category(policy_text: Optional[str]) -> Optional[CancelCategory]:
    """Classify free-text cancellation policy into free, partial, or non_refundable."""
    if not policy_text or not policy_text.strip():
        return None
    p = policy_text.lower()
    if "free cancellation" in p:
        return "free"
    if any(term in p for term in ["non-refundable", "non refundable", "no refund", "nonrefundable"]):
        return "non_refundable"
    return "partial"


def determine_status(
    reached_payment_page: bool,
    final_price: Optional[float],
    evidence: list,
    reconciliation: Optional[str],
    blocker: Optional[str] = None,
    occupancy_mismatch: bool = False,
    currency_mismatch: bool = False,
) -> Status:
    """Evaluate offer verification status by the strict TinyTravel product rules.
    
    Invariant 2: verified requires ALL: reached_payment_page==true, price_final_payable!=null,
    at least one evidence item, fee_lines sum to price_final_payable within +/-1%.
    Occupancy or currency mismatch causes offer to be unverified (non-comparable), with blocker=None.
    """
    if occupancy_mismatch or currency_mismatch:
        return "unverified"
    if (
        reached_payment_page
        and final_price is not None
        and len(evidence) > 0
        and reconciliation == "ok"
    ):
        return "verified"
    if blocker is not None:
        return "blocked"
    return "unverified"


def verified(o: dict) -> bool:
    """Check if offer dictionary meets all verified invariants."""
    return (
        bool(o.get("reached_payment_page"))
        and o.get("price_final_payable") is not None
        and len(o.get("evidence", [])) > 0
        and reconciles(o.get("fee_lines", []), o["price_final_payable"])
    )


def transparency_score(offer: dict, recheck: Optional[dict] = None) -> dict:
    """Compute transparency score (0-100) and component breakdown.
    
    Formula:
    - fee_leak (max 50): max(0, 50 * (1 - leak / 40))
    - addons_pressure (max 20): max(0, 20 - 5 * len(preselected_addons) - 5 * len(urgency_messages))
    - price_stability (max 20): only if re-check exists: 20 * max(0, 1 - pct_change / 10)
    - evidence (max 10): 10 if listing + room + payment evidence all exist, else proportionally less
    - score: round(sum_of_present_components / max_possible_of_present_components * 100)
    - note: 'observed on this run' plus '; stability N/A, weights re-normalised' when no re-check
    - Unverified / blocked offers: score=None, breakdown=None, note='N/A (not verified)'
    """
    if offer.get("status") != "verified":
        return {
            "score": None,
            "breakdown": None,
            "note": "N/A (not verified)",
        }

    leak = offer.get("fee_leak_pct")
    if leak is not None:
        fee_leak_comp = round(max(0.0, 50.0 * (1.0 - leak / 40.0)), 1)
    else:
        fee_leak_comp = 0.0

    addons = offer.get("preselected_addons") or []
    urgency = offer.get("urgency_or_scarcity_messages") or []
    addons_comp = max(0.0, 20.0 - 5.0 * len(addons) - 5.0 * len(urgency))

    # Evidence rule: 10 if all 3 critical checkout steps ('listing', 'room', 'payment') are present;
    # otherwise proportionally 10.0 * present_steps / 3.0 rounded to 1 decimal place.
    ev_list = offer.get("evidence") or []
    present_steps = set(
        e.get("step")
        for e in ev_list
        if isinstance(e, dict) and e.get("step") in ("listing", "room", "payment")
    )
    if len(present_steps) == 3:
        evidence_comp = 10
    else:
        evidence_comp = round(10.0 * len(present_steps) / 3.0, 1)

    # Price stability component (max 20): only if recheck is present
    if recheck:
        if "previous" in recheck and "current" in recheck:
            prev_amt = float(recheck["previous"].get("amount", 0.0))
            curr_amt = float(recheck["current"].get("amount", 0.0))
            pct_change = abs(curr_amt - prev_amt) / prev_amt * 100.0 if prev_amt > 0 else 0.0
        elif "delta_pct" in recheck:
            pct_change = abs(float(recheck["delta_pct"]))
        else:
            pct_change = 0.0
        stability_comp = round(max(0.0, 20.0 * (1.0 - pct_change / 10.0)), 1)
        max_possible = 100.0
        note = "observed on this run"
    else:
        stability_comp = None
        max_possible = 80.0
        note = "observed on this run; stability N/A, weights re-normalised"

    present_comps = [fee_leak_comp, addons_comp, evidence_comp]
    if stability_comp is not None:
        present_comps.append(stability_comp)

    total_score = round(sum(present_comps) / max_possible * 100.0)

    return {
        "score": total_score,
        "breakdown": {
            "fee_leak": fee_leak_comp,
            "addons_pressure": int(addons_comp) if addons_comp.is_integer() else addons_comp,
            "price_stability": stability_comp,
            "evidence": evidence_comp,
        },
        "note": note,
    }


def validate_no_cross_level_ranking(offers: list[dict]) -> None:
    """Enforce invariant: no ranking across verification levels.
    
    Raises ValueError if offers to be ranked contain mixed verification_level values.
    Indicative listing offers (e.g. Google Hotels) must never be ranked alongside checkout-verified offers.
    """
    levels = {o.get("verification_level", "checkout") for o in offers if o.get("verification_level")}
    if len(levels) > 1:
        raise ValueError(
            f"Cross-verification-level ranking violation: cannot rank across mixed levels {levels}. "
            f"Indicative listing offers (e.g. Google Hotels) must never be ranked alongside checkout-verified offers."
        )


def rank_offers(
    offers: list[dict],
    hotels: Union[list[dict], dict],
    deal_mode: str = "best_value",
    verification_level: Optional[str] = "checkout",
) -> list[dict]:
    """Rank VERIFIED offers according to deal mode weights.
    
    Enforces invariant: No ranking across verification levels.
    Listing offers (e.g. Google Hotels) are indicative-only and cannot be ranked alongside checkout offers.
    
    Components (each 0-100):
    - price: 100 * min_payable / payable across verified offers
    - prefs: 100 * (breakfast_present + free_cancellation) / 2
    - cancellation: free 100 / partial 50 / non_refundable 0
    - quality: rating / 5 * 100 (if rating is None, quality is dropped and weights re-normalised)
    - transparency: transparency score (0-100)
    
    Weights [price, prefs, cancellation, quality, transparency]:
    - lowest_price: 60/15/15/0/10
    - best_value: 35/25/20/10/10
    - most_transparent: 25/15/15/0/45
    
    total = round(sum(c * w) / sum(w present), 1), sorted descending.
    """
    # Check for cross-level ranking violation among candidate offers with prices
    eval_levels = {
        o.get("verification_level", "checkout")
        for o in offers
        if o.get("price_final_payable") is not None or o.get("price_shown_on_listing") is not None
    }
    if len(eval_levels) > 1:
        raise ValueError(
            f"Cross-level ranking violation: cannot rank across mixed verification levels {eval_levels}. "
            f"Indicative listing offers (e.g. Google Hotels) must never be ranked alongside checkout-verified offers."
        )

    target_level = verification_level or "checkout"
    currencies = [
        o.get("currency", "INR") for o in offers
        if o.get("status") == "verified" and o.get("price_final_payable") is not None
        and o.get("verification_level", "checkout") == target_level
    ]
    dominant_currency = Counter(currencies).most_common(1)[0][0] if currencies else "INR"

    verified_offers = [
        o for o in offers
        if o.get("status") == "verified"
        and o.get("price_final_payable") is not None
        and o.get("currency", "INR") == dominant_currency
        and o.get("verification_level", "checkout") == target_level
    ]
    if not verified_offers:
        return []

    min_payable = min(float(o["price_final_payable"]) for o in verified_offers)

    if isinstance(hotels, list):
        hotels_map = {h["hotel_id"]: h for h in hotels if isinstance(h, dict) and "hotel_id" in h}
    elif isinstance(hotels, dict):
        hotels_map = hotels
    else:
        hotels_map = {}

    base_weights = DEAL_MODE_WEIGHTS.get(deal_mode, DEAL_MODE_WEIGHTS["best_value"])

    ranking_items = []
    for o in verified_offers:
        payable = float(o["price_final_payable"])
        p_comp = round(100.0 * min_payable / payable, 1)

        # Prefs: breakfast present + free cancellation
        bf = 1 if "breakfast" in (o.get("meal_plan") or "").lower() else 0
        fc = 1 if o.get("cancellation_category") == "free" else 0
        prefs_comp = round(100.0 * (bf + fc) / 2.0, 1)

        # Cancellation
        cc = o.get("cancellation_category")
        canc_comp = 100 if cc == "free" else (50 if cc == "partial" else 0)

        # Quality
        hotel = hotels_map.get(o.get("hotel_id"), {})
        rating = hotel.get("rating") if isinstance(hotel, dict) else None

        # Transparency
        tr = o.get("transparency")
        if isinstance(tr, dict) and tr.get("score") is not None:
            trans_comp = tr["score"]
        else:
            computed_tr = transparency_score(o)
            trans_comp = computed_tr.get("score", 0)

        comps = {
            "price": p_comp,
            "prefs": prefs_comp,
            "cancellation": canc_comp,
        }
        active_weights = {
            "price": base_weights["price"],
            "prefs": base_weights["prefs"],
            "cancellation": base_weights["cancellation"],
        }

        # Quality component
        if rating is not None and base_weights.get("quality", 0) > 0:
            comps["quality"] = round(float(rating) / 5.0 * 100.0, 1)
            active_weights["quality"] = base_weights["quality"]

        comps["transparency"] = trans_comp
        active_weights["transparency"] = base_weights["transparency"]

        total_weight = sum(active_weights.values())
        if total_weight > 0:
            total = round(
                sum(comps[k] * active_weights[k] for k in comps if k in active_weights) / total_weight,
                1,
            )
        else:
            total = 0.0

        full_components = {
            "price": p_comp,
            "prefs": prefs_comp,
            "cancellation": canc_comp,
            "quality": round(float(rating) / 5.0 * 100.0, 1) if rating is not None else None,
            "transparency": trans_comp,
        }
        full_weights = dict(base_weights)

        ranking_items.append({
            "offer_id": o["offer_id"],
            "total": total,
            "components": full_components,
            "weights": full_weights,
            "_payable": payable,
        })

    # Sort descending by total, then price ascending (cheaper first), then offer_id
    ranking_items.sort(key=lambda r: (-r["total"], r["_payable"], r["offer_id"]))

    for r in ranking_items:
        r.pop("_payable", None)

    return ranking_items


def _format_amount(val: Optional[float]) -> str:
    if val is None:
        return "N/A"
    return f"{int(round(val)):,}"


def _pick_scope_verdicts(
    scope_offers: list[dict],
    ranking: list[dict],
) -> dict:
    currencies = [
        o.get("currency", "INR") for o in scope_offers
        if o.get("status") == "verified" and o.get("price_final_payable") is not None
    ]
    dominant_currency = Counter(currencies).most_common(1)[0][0] if currencies else "INR"

    verified = [
        o for o in scope_offers
        if o.get("status") == "verified"
        and o.get("price_final_payable") is not None
        and o.get("currency", "INR") == dominant_currency
    ]
    if not verified:
        return {
            "cheapest_verified": None,
            "safe_cheapest": None,
            "best_for_you": None,
            "headlines": {},
        }

    offers_by_id = {o["offer_id"]: o for o in verified}

    # Cheapest verified: lowest payable (any policy)
    cheapest = min(verified, key=lambda o: float(o["price_final_payable"]))

    # Safe cheapest: lowest payable with cancellation_category == free
    safe_candidates = [
        o for o in verified
        if o.get("cancellation_category") == "free"
    ]
    safe = (
        min(safe_candidates, key=lambda o: float(o["price_final_payable"]))
        if safe_candidates
        else None
    )

    # Best for you: top of ranking within scope, or cheapest fallback
    scope_offer_ids = set(offers_by_id.keys())
    ranked_in_scope = [r["offer_id"] for r in ranking if r.get("offer_id") in scope_offer_ids]
    best_id = ranked_in_scope[0] if ranked_in_scope else cheapest["offer_id"]
    best = offers_by_id[best_id]

    # Headlines matching fixtures exactly:
    # cheapest_verified: "{hotel_name} on {site}: you pay {currency} {payable}, listing showed {currency} {listing}"
    h_cheapest = (
        f"{cheapest.get('hotel_name', '')} on {cheapest.get('site', '')}: "
        f"you pay {cheapest.get('currency', 'INR')} {_format_amount(cheapest.get('price_final_payable'))}, "
        f"listing showed {cheapest.get('currency', 'INR')} {_format_amount(cheapest.get('price_shown_on_listing'))}"
    )

    # safe_cheapest: "{hotel_name} on {site}: {currency} {payable} with free cancellation"
    h_safe = (
        f"{safe.get('hotel_name', '')} on {safe.get('site', '')}: "
        f"{safe.get('currency', 'INR')} {_format_amount(safe.get('price_final_payable'))} with free cancellation"
        if safe
        else ""
    )

    # best_for_you: "{hotel_name} on {site}: {currency} {payable}"
    h_best = (
        f"{best.get('hotel_name', '')} on {best.get('site', '')}: "
        f"{best.get('currency', 'INR')} {_format_amount(best.get('price_final_payable'))}"
    )

    headlines = {
        "cheapest_verified": h_cheapest,
        "safe_cheapest": h_safe,
        "best_for_you": h_best,
    }

    return {
        "cheapest_verified": cheapest["offer_id"],
        "safe_cheapest": safe["offer_id"] if safe else None,
        "best_for_you": best["offer_id"],
        "headlines": headlines,
    }


def pick_verdicts(
    offers: list[dict],
    ranking: list[dict],
    hotel_id: Optional[str] = None,
) -> dict:
    """Pick cheapest, safe-cheapest, and best-for-you verdicts and headlines.
    
    If hotel_id is specified, returns verdicts for that single hotel scope.
    If hotel_id is None, computes verdicts overall and per hotel.
    """
    if hotel_id is not None:
        h_offers = [o for o in offers if o.get("hotel_id") == hotel_id]
        return _pick_scope_verdicts(h_offers, ranking)

    # Overall scope
    overall = _pick_scope_verdicts(offers, ranking)

    # Per-hotel scope
    hotel_ids = []
    for o in offers:
        hid = o.get("hotel_id")
        if hid and hid not in hotel_ids:
            hotel_ids.append(hid)

    per_hotel = {}
    for hid in hotel_ids:
        h_offers = [o for o in offers if o.get("hotel_id") == hid]
        per_hotel[hid] = _pick_scope_verdicts(h_offers, ranking)

    result = dict(overall)
    result["overall"] = overall
    result["per_hotel"] = per_hotel
    return result


def summary_strip(offers: list[dict], listings: Union[list[dict], int] = 0) -> dict:
    """Generate summary strip metrics across all offers and listings."""
    if isinstance(listings, int):
        listings_found = listings
    elif isinstance(listings, (list, tuple)):
        listings_found = len(listings)
    else:
        listings_found = 0

    unique_hotels = len(set(o["hotel_id"] for o in offers if o.get("hotel_id")))
    verified_count = sum(1 for o in offers if o.get("status") == "verified")
    unverified_count = sum(1 for o in offers if o.get("status") == "unverified")
    blocked_count = sum(1 for o in offers if o.get("status") == "blocked")

    verified_leaks = [
        o["fee_leak_pct"]
        for o in offers
        if o.get("status") == "verified" and o.get("fee_leak_pct") is not None
    ]
    avg_leak = (
        round(sum(verified_leaks) / len(verified_leaks), 1)
        if verified_leaks
        else None
    )

    return {
        "listings_found": listings_found,
        "unique_hotels": unique_hotels,
        "verified": verified_count,
        "unverified": unverified_count,
        "blocked": blocked_count,
        "avg_fee_leak_pct": avg_leak,
    }


def _normalize_tier(room_type: Optional[str]) -> str:
    if not room_type:
        return "standard"
    rt = room_type.lower()
    if any(k in rt for k in ["suite", "presidential", "penthouse"]):
        return "suite"
    elif any(k in rt for k in ["executive", "club"]):
        return "executive"
    elif any(k in rt for k in ["deluxe", "superior", "premium"]):
        return "deluxe"
    elif any(k in rt for k in ["villa", "cottage"]):
        return "villa"
    return "standard"


def non_comparable_warnings(offers: list[dict]) -> list[dict]:
    """Detect and describe differences on cancellation, meal plan, occupancy, or room tier within each hotel group."""
    by_hotel: dict[str, list[dict]] = {}
    for o in offers:
        hid = o.get("hotel_id", "")
        if hid:
            by_hotel.setdefault(hid, []).append(o)

    warnings = []
    for hid, h_offers in by_hotel.items():
        verified = [o for o in h_offers if o.get("status") == "verified"]
        if len(verified) < 2:
            continue

        # 1. Cancellation category comparison
        categories = [o.get("cancellation_category") for o in verified]
        cat_counts = Counter(categories)
        majority_cat, majority_count = cat_counts.most_common(1)[0]

        if majority_count < len(verified):
            majority_sites = [
                o.get("site", "")
                for o in verified
                if o.get("cancellation_category") == majority_cat
            ]
            if len(majority_sites) == 2:
                maj_sites_str = f"{majority_sites[0]} and {majority_sites[1]}"
            else:
                maj_sites_str = ", ".join(majority_sites)

            maj_cat_label = (
                "free-cancellation" if majority_cat == "free" else (majority_cat or "other")
            )

            for o in verified:
                c = o.get("cancellation_category")
                if c != majority_cat:
                    diff_label = (
                        "non-refundable"
                        if c == "non_refundable"
                        else (c or "different policy")
                    )
                    site_name = o.get("site", "")
                    msg = (
                        f"{site_name} room is {diff_label}; "
                        f"not comparable with the {maj_cat_label} rooms on {maj_sites_str}."
                    )
                    warnings.append({
                        "hotel_id": hid,
                        "offer_id": o["offer_id"],
                        "message": msg,
                    })

        # 2. Meal plan comparison
        meals = [o.get("meal_plan", "").strip().lower() for o in verified]
        meal_counts = Counter(meals)
        if len(meal_counts) > 1:
            maj_meal, maj_m_count = meal_counts.most_common(1)[0]
            maj_m_sites = [o.get("site", "") for o in verified if o.get("meal_plan", "").strip().lower() == maj_meal]
            maj_m_str = " and ".join(maj_m_sites) if len(maj_m_sites) == 2 else ", ".join(maj_m_sites)
            for o in verified:
                m = o.get("meal_plan", "").strip().lower()
                if m != maj_meal and not any(w["offer_id"] == o["offer_id"] and "meal plan" in w["message"] for w in warnings):
                    site_name = o.get("site", "")
                    warnings.append({
                        "hotel_id": hid,
                        "offer_id": o["offer_id"],
                        "message": f"{site_name} meal plan '{o.get('meal_plan', '')}'; not comparable with '{maj_meal}' on {maj_m_str}."
                    })

        # 3. Occupancy comparison
        occs = [o.get("max_occupancy") for o in verified if o.get("max_occupancy") is not None]
        occ_counts = Counter(occs)
        if len(occ_counts) > 1:
            maj_occ, _ = occ_counts.most_common(1)[0]
            maj_o_sites = [o.get("site", "") for o in verified if o.get("max_occupancy") == maj_occ]
            maj_o_str = " and ".join(maj_o_sites) if len(maj_o_sites) == 2 else ", ".join(maj_o_sites)
            for o in verified:
                occ = o.get("max_occupancy")
                if occ != maj_occ and not any(w["offer_id"] == o["offer_id"] and "occupancy" in w["message"] for w in warnings):
                    site_name = o.get("site", "")
                    warnings.append({
                        "hotel_id": hid,
                        "offer_id": o["offer_id"],
                        "message": f"{site_name} fits {occ} guests; not comparable with {maj_occ} guests on {maj_o_str}."
                    })

        # 4. Room tier comparison
        tiers = [_normalize_tier(o.get("room_type")) for o in verified]
        tier_counts = Counter(tiers)
        if len(tier_counts) > 1:
            maj_tier, _ = tier_counts.most_common(1)[0]
            maj_t_sites = [o.get("site", "") for o in verified if _normalize_tier(o.get("room_type")) == maj_tier]
            maj_t_str = " and ".join(maj_t_sites) if len(maj_t_sites) == 2 else ", ".join(maj_t_sites)
            for o in verified:
                t = _normalize_tier(o.get("room_type"))
                if t != maj_tier and not any(w["offer_id"] == o["offer_id"] and "tier" in w["message"] for w in warnings):
                    site_name = o.get("site", "")
                    warnings.append({
                        "hotel_id": hid,
                        "offer_id": o["offer_id"],
                        "message": f"{site_name} room is {t} tier; not comparable with {maj_tier} tier rooms on {maj_t_str}."
                    })

    # Currency mismatch check: detect non-INR or currency differences across offers
    for o in offers:
        curr = o.get("currency")
        if curr and curr != "INR":
            oid = o.get("offer_id", "")
            if not any(w["offer_id"] == oid for w in warnings):
                site_name = o.get("site", "Platform")
                warnings.append({
                    "hotel_id": o.get("hotel_id", ""),
                    "offer_id": oid,
                    "message": f"{site_name} returned price in {curr}; not comparable with INR offers without currency conversion.",
                })

    return warnings
