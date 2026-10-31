"""Checkout Verification Agent.
Autonomous TinyFish browser agent probing through hotel checkouts to verify all-in payable price.
"""
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
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
    from ..services.fees import classify_fee_label
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
    from services.fees import classify_fee_label

IST = timezone(timedelta(hours=5, minutes=30))


def build_goal(hotel_name: str, req: dict, platform: Optional[str] = None) -> str:
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

    p = (platform or req.get("platform") or "").lower().replace(".", "").replace(" ", "").replace("-", "")

    platform_notes = ""
    if p in ("booking", "bookingcom"):
        platform_notes = (
            f"Booking.com specific:\n"
            f"- Search for \"{hotel_name}\" in the destination/hotel search box to navigate to \"{hotel_name}\".\n"
            f"- Currency MUST be INR. If prices display in USD, switch the currency picker to INR or record the property's INR amount (Rs. X) as the prices and currency.\n"
            f"- Pick a room whose listed occupancy is >= {guests} adults.\n"
            "- Don't browse other properties or read reviews.\n"
            "- Record the booked room's 'X adults' text in notes.\n"
            "- Set max_occupancy strictly from the booked room's occupancy text (>= 2).\n"
            "- Fee reconciliation: If taxes are already included in the room total (e.g. 'includes taxes and fees'), do not add taxes as an extra fee; fee_lines must sum to price_final_payable within 1%.\n"
        )
    elif p == "agoda":
        platform_notes = (
            f"Agoda specific:\n"
            f"- Search for \"{hotel_name}\" in the Agoda search box to locate and open \"{hotel_name}\".\n"
            "- Ignore rooms showing max 1 adult; select only a room fitting 2 adults.\n"
            "- On the booking summary page, copy the room name + guest count text verbatim into notes, and set max_occupancy from that text, never from rejected rooms.\n"
        )

    return (
        f"Open the provided URL. Search for \"{hotel_name}\" in {city} for {check_in} to {check_out}, {guests} adults, {rooms} room.\n"
        f"Type \"{hotel_name}\" into the search input if needed to locate and select the hotel named \"{hotel_name}\" (if not found after searching, return blocker \"other\" with notes).\n"
        f"Select the cheapest room that fits {guests} adults. {prefs_clause}\n"
        f"{platform_notes}"
        "Proceed as a GUEST through checkout using: Name \"Test Guest\", email \"test.guest+probe@example.com\", phone \"9000000000\".\n"
        "Record the displayed total at each step in price_trail with the currency shown on screen. Do not convert currencies.\n"
        "Record every fee line, pre-selected add-on, and any urgency/scarcity message.\n"
        "Extract hotel_url, listing_page_text (text from listing card), and payment_page_text (price breakdown text from payment page).\n"
        "max_occupancy and room_type must describe the room in the final booking summary, copying the \"X adults\" text from that page.\n"
        "price_shown_on_listing must be the price of the same room as the final payable, or null. Never record a listing price from a different room.\n"
        "Ensure price_trail includes each observed step: 'listing', 'room', 'traveller_details', 'payment'.\n"
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
            f"ss={city}&checkin={check_in}&checkout={check_out}&group_adults={guests}&no_rooms={rooms}&selected_currency=INR&group_children=0"
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


def classify_blocker(error_text: Optional[str]) -> Optional[str]:
    """Map observed failure/error text to standard Blocker enum."""
    if not error_text:
        return None
    err = str(error_text).lower()
    if any(k in err for k in ["captcha", "challenge", "cloudflare", "datadome", "perimeterx", "bot"]):
        return "captcha"
    if any(k in err for k in ["login", "sign in", "signin", "authenticate", "account required"]):
        return "login"
    if any(k in err for k in ["otp", "verification code", "2fa", "sms code", "one time password"]):
        return "otp"
    if any(k in err for k in ["timeout", "timed out", "deadline"]):
        return "timeout"
    return "other"


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

    goal = build_goal(hotel_name, req, platform=platform)
    output_schema = ProbeResult.model_json_schema()

    default_timeout = int(os.getenv("AGENT_TIMEOUT_S", "600" if os.getenv("DATA_MODE") == "live" else "360"))
    timeout_s = req.get("timeout_s", default_timeout)

    run: AgentRun = await run_agent(
        url=url,
        goal=goal,
        output_schema=output_schema,
        profile=profile,
        timeout_s=timeout_s,
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
    blocker = classify_blocker(probe_data.get("blocker"))
    policy = probe_data.get("cancellation_policy")
    price_listing = probe_data.get("price_shown_on_listing")
    price_room = probe_data.get("price_shown_on_room_selection")
    price_payable = probe_data.get("price_final_payable")
    raw_fee_lines = probe_data.get("fee_lines") or []
    fee_lines = []
    for fl in raw_fee_lines:
        if isinstance(fl, dict):
            fl_copy = dict(fl)
            fl_copy["fee_kind"] = fl_copy.get("fee_kind") or classify_fee_label(fl_copy.get("label", ""))
            fee_lines.append(fl_copy)
        else:
            fee_lines.append(fl)
    price_trail = probe_data.get("price_trail") or []
    currency = probe_data.get("currency") or "INR"

    listing_page_text = probe_data.get("listing_page_text")
    payment_page_text = probe_data.get("payment_page_text")
    notes = probe_data.get("notes") or (run.error or "")

    # Handle run level timeout / errors
    if run.status == "timeout":
        blocker = "timeout"
        furthest_step = "timeout"
        reached_payment_page = False
    elif run.status == "failed" and not blocker:
        blocker = classify_blocker(run.error) or "other"

    # Verify max_occupancy fits requested guests (do NOT mutate reached_payment_page)
    req_guests = int(req.get("guests", 2))
    max_occ = probe_data.get("max_occupancy")
    occupancy_mismatch = False
    if max_occ is not None and max_occ < req_guests:
        occupancy_mismatch = True
        notes = (notes + f" [Occupancy mismatch: room fits {max_occ} adults but search requested {req_guests}]").strip()

    # Verify currency matches requested search currency (do NOT mutate reached_payment_page)
    req_curr = req.get("currency", "INR")
    currency_mismatch = False
    if currency and req_curr and currency.upper() != req_curr.upper():
        currency_mismatch = True
        notes = (notes + f" [Currency mismatch: platform returned {currency} but search requested {req_curr}]").strip()

    # Blocked is only for captcha/login/otp/timeout/other that really stopped the run.
    # If the payment page was reached and payable price obtained, the run was not stopped by a blocker.
    if reached_payment_page and price_payable is not None:
        blocker = None

    # On occupancy mismatch or currency mismatch, blocker must be null (reason is in notes, status is unverified)
    if occupancy_mismatch or currency_mismatch:
        blocker = None

    # price_shown_on_listing must be the price of the same room as the final payable, or null.
    # Never compute fee_leak_pct from a different room.
    same_room = probe_data.get("listing_price_same_room", True)
    if not same_room:
        price_listing = None

    c_cat = cancellation_category(policy)
    recon = reconciliation_status(fee_lines, price_payable)

    hotel_slug = hotel_name.lower().replace(" ", "_")
    site_slug = platform.lower().replace(".", "").replace(" ", "")
    offer_id = req.get("offer_id") or f"off_{site_slug}_{hotel_slug[:8]}"
    hotel_id = req.get("hotel_id") or f"h_{hotel_slug[:8]}"

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
        offer_id=offer_id,
    )

    status = determine_status(
        reached_payment_page=reached_payment_page,
        final_price=price_payable,
        evidence=evidence,
        reconciliation=recon,
        blocker=blocker,
        occupancy_mismatch=occupancy_mismatch,
        currency_mismatch=currency_mismatch,
    )

    leak = fee_leak_pct(price_listing, price_payable, same_room=same_room) if status == "verified" else None


    if not is_mock:
        try:
            results_dir = Path(__file__).resolve().parents[2] / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            raw_path = results_dir / f"gate_{hotel_slug}_{site_slug}_raw.json"
            raw_payload = {
                "run_id": run.run_id,
                "streaming_url": run.streaming_url,
                "status": run.status,
                "steps": run.steps,
                "cost_usd": run.cost_usd,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "result": run.result,
                "raw": run.raw,
                "error": run.error,
            }
            raw_path.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
        except Exception:
            pass

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
        "notes": notes,
        "fee_leak_pct": leak,

        "evidence": evidence,
        "mock": is_mock,
        "listing_page_text": listing_page_text,
        "payment_page_text": payment_page_text,
        "transparency": (
            {"score": None, "breakdown": None, "note": "N/A (not verified)"}
            if status != "verified"
            else (
                run.raw.get("transparency")
                if isinstance(run.raw, dict) and run.raw.get("transparency")
                else transparency_score({
                    "status": status,
                    "fee_leak_pct": leak,
                    "preselected_addons": probe_data.get("preselected_addons", []),
                    "urgency_or_scarcity_messages": probe_data.get("urgency_or_scarcity_messages", []),
                    "evidence": evidence,
                })
            )
        ),
    }
