"""Checkout Verification Agent.
Autonomous TinyFish browser agent probing through hotel checkouts to verify all-in payable price.
"""
from datetime import datetime, timezone, timedelta
import os
from typing import Callable, Optional, Any
from urllib.parse import quote_plus

try:
    from ..models import ProbeResult, Offer
    from ..services.tinyfish import run_agent, AgentRun
    from ..services.evidence import build_evidence
    from ..services.scoring import (
        fee_leak_pct,
        reconciliation_status,
        cancellation_category,
        determine_status,
        transparency_score,
    )
except ImportError:
    from models import ProbeResult, Offer
    from services.tinyfish import run_agent, AgentRun
    from services.evidence import build_evidence
    from services.scoring import (
        fee_leak_pct,
        reconciliation_status,
        cancellation_category,
        determine_status,
        transparency_score,
    )

IST = timezone(timedelta(hours=5, minutes=30))


def build_goal(hotel_name: str, req: dict) -> str:
    """Construct the goal prompt for TinyFish, keeping safety instructions verbatim."""
    city = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = req.get("guests", 2)
    rooms = req.get("rooms", 1)

    must_have = req.get("must_have", {})
    prefs = []
    if isinstance(must_have, dict):
        if must_have.get("free_cancellation"):
            prefs.append("free cancellation")
        if must_have.get("breakfast"):
            prefs.append("breakfast included")
    elif isinstance(must_have, (list, set)):
        if "free_cancellation" in must_have:
            prefs.append("free cancellation")
        if "breakfast" in must_have:
            prefs.append("breakfast included")

    if prefs:
        prefs_clause = (
            f"Prefer {', '.join(prefs)}. If no matching room satisfies these preferences, "
            f"select the cheapest room that fits {guests} adults, and report the actual meal plan and cancellation policy."
        )
    else:
        prefs_clause = "Prefer free cancellation; otherwise cheapest, and report the cancellation policy."

    return (
        f"Open the provided URL. Search for hotels in {city} for {check_in} to {check_out}, {guests} adults, {rooms} room.\n"
        f"Find the hotel named \"{hotel_name}\" (exact name; if not found, return blocker \"other\" with notes).\n"
        f"Select the cheapest room that fits {guests} adults. {prefs_clause}\n"
        "Proceed as a GUEST through checkout using: Name \"Test Guest\", email \"test.guest+probe@example.com\", phone \"9000000000\".\n"
        "Record the displayed total at each step in price_trail with the currency shown on screen. Do not convert currencies.\n"
        "Record every fee line, pre-selected add-on, and any urgency/scarcity message.\n"
        "STOP at the payment page. Never enter payment details, never click pay/confirm/book, never log in, never enter an OTP, never create an account.\n"
        "If blocked (login, OTP, captcha, empty page), stop and return the blocker.\n"
        "Use at most 30 steps. Return ONLY JSON in the given schema."
    )


def site_url(platform: str, req: dict) -> str:
    """Build pre-filled direct search URL for confirmed platforms.

    Raises NotImplementedError when exact query parameters have not been confirmed by real probes.
    """
    p = platform.lower().replace(".", "").replace(" ", "").replace("-", "")
    city = quote_plus(req.get("destination", "Bengaluru"))
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = req.get("guests", 2)
    rooms = req.get("rooms", 1)

    if p == "cleartrip":
        return (
            f"https://www.cleartrip.com/hotels/results?"
            f"city={city}&chk_in={check_in}&chk_out={check_out}&adults={guests}&num_rooms={rooms}"
        )
    elif p == "agoda":
        return (
            f"https://www.agoda.com/search?"
            f"city={city}&checkIn={check_in}&checkOut={check_out}&rooms={rooms}&adults={guests}&currency=INR"
        )
    elif p in ("booking", "bookingcom"):
        return (
            f"https://www.booking.com/searchresults.html?"
            f"ss={city}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}"
        )
    elif p == "easemytrip":
        raise NotImplementedError(
            "EaseMyTrip direct search URL query parameters are unconfirmed (date picker was too slow in probe)."
        )
    elif p == "makemytrip":
        raise NotImplementedError(
            "MakeMyTrip direct search URL query parameters are unconfirmed (blocked on lite profile; stealth profile untested)."
        )
    elif p == "goibibo":
        raise NotImplementedError(
            "Goibibo direct search URL query parameters are unconfirmed (blocked on lite profile; stealth profile untested)."
        )
    else:
        raise NotImplementedError(f"Platform '{platform}' direct search URL is unknown.")


async def verify_offer(
    platform: str,
    hotel_name: str,
    req: dict,
    *,
    profile: str = "lite",
    on_stream_url: Optional[Callable[[str], Any]] = None,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> dict:
    """Execute end-to-end checkout verification for an offer, post-processing observed results."""
    # Allow explicit URL override (useful for CLI manual probes or tests)
    explicit_url = req.get("url")
    url = explicit_url if explicit_url else site_url(platform, req)

    goal = build_goal(hotel_name, req)
    output_schema = ProbeResult.model_json_schema()

    run: AgentRun = await run_agent(
        url=url,
        goal=goal,
        output_schema=output_schema,
        profile=profile,
        timeout_s=req.get("timeout_s", 360),
        on_stream_url=on_stream_url,
        on_progress=on_progress,
    )

    # Validate raw result with Pydantic ProbeResult model
    if run.result:
        try:
            validated_probe = ProbeResult.model_validate(run.result)
            probe_data = validated_probe.model_dump()
        except Exception:
            probe_data = run.result
    else:
        probe_data = {}

    # Extract observed fields
    site = probe_data.get("site") or platform
    reached_payment_page = bool(probe_data.get("reached_payment_page", False))
    furthest_step = probe_data.get("furthest_step") or ("payment" if reached_payment_page else "unknown")
    blocker = probe_data.get("blocker")
    policy = probe_data.get("cancellation_policy")
    price_listing = probe_data.get("price_shown_on_listing")
    price_room = probe_data.get("price_shown_on_room_selection")
    price_payable = probe_data.get("price_final_payable")
    fee_lines = probe_data.get("fee_lines") or []
    price_trail = probe_data.get("price_trail") or []
    currency = probe_data.get("currency") or "INR"

    listing_page_text = probe_data.get("listing_page_text")
    payment_page_text = probe_data.get("payment_page_text")

    # Post-processing via pure functions
    c_cat = cancellation_category(policy)
    recon = reconciliation_status(fee_lines, price_payable)

    # Build evidence items
    existing_ev = run.raw.get("evidence") if isinstance(run.raw, dict) else None
    is_mock = os.getenv("TINYFISH_FAKE") == "1" or os.getenv("DATA_MODE", "mock") == "mock"

    evidence = build_evidence(
        streaming_url=run.streaming_url,
        listing_page_text=listing_page_text,
        payment_page_text=payment_page_text,
        price_shown_on_listing=price_listing,
        price_shown_on_room_selection=price_room,
        price_final_payable=price_payable,
        started_at=run.started_at,
        finished_at=run.finished_at,
        currency=currency,
        mock=is_mock,
        existing_evidence=existing_ev,
    )

    status = determine_status(
        reached_payment_page=reached_payment_page,
        final_price=price_payable,
        evidence=evidence,
        reconciliation=recon,
        blocker=blocker,
    )

    leak = fee_leak_pct(price_listing, price_payable) if status == "verified" else None

    hotel_slug = hotel_name.lower().replace(" ", "_")[:8]
    site_slug = platform.lower().replace(".", "").replace(" ", "")
    offer_id = req.get("offer_id") or f"off_{site_slug}_{hotel_slug}"
    hotel_id = req.get("hotel_id") or f"h_{hotel_slug}"

    return {
        "offer_id": offer_id,
        "hotel_id": hotel_id,
        "run_id": run.run_id,
        "streaming_url": run.streaming_url,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "steps": run.steps,
        "cost_usd": run.cost_usd,
        "status": status,
        "reconciliation": recon,
        "cancellation_category": c_cat,
        "site": site,
        "reached_payment_page": reached_payment_page,
        "furthest_step": furthest_step,
        "blocker": blocker,
        "hotel_name": probe_data.get("hotel_name") or hotel_name,
        "hotel_url": probe_data.get("hotel_url") or url,
        "room_type": probe_data.get("room_type", ""),
        "max_occupancy": probe_data.get("max_occupancy", req.get("guests", 2)),
        "meal_plan": probe_data.get("meal_plan", ""),
        "cancellation_policy": policy or "",
        "price_shown_on_listing": price_listing,
        "price_shown_on_room_selection": price_room,
        "price_final_payable": price_payable,
        "fee_lines": fee_lines,
        "preselected_addons": probe_data.get("preselected_addons", []),
        "urgency_or_scarcity_messages": probe_data.get("urgency_or_scarcity_messages", []),
        "price_trail": price_trail,
        "currency": currency,
        "notes": probe_data.get("notes", run.error or ""),
        "fee_leak_pct": leak,
        "evidence": evidence,
        "mock": is_mock,
        "listing_page_text": listing_page_text,
        "payment_page_text": payment_page_text,
        "transparency": (
            run.raw.get("transparency")
            if isinstance(run.raw, dict) and run.raw.get("transparency")
            else transparency_score({
                "status": status,
                "fee_leak_pct": leak,
                "preselected_addons": probe_data.get("preselected_addons", []),
                "urgency_or_scarcity_messages": probe_data.get("urgency_or_scarcity_messages", []),
                "evidence": evidence,
            })
        ),
    }
