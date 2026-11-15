"""
Agent Router: Configurable Execution Strategy (AGENT_RUNNER=own|tinyfish|hybrid).
Supports running deterministic own Playwright playbooks (Cleartrip, Agoda)
or TinyFish autonomous browser agent, with evidence artifacts (screenshots, page text).
"""
import asyncio
from datetime import datetime, timezone, timedelta
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .scoring import (
    fee_leak_pct,
    reconciliation_status,
    cancellation_category,
    determine_status,
    transparency_score,
)
from .evidence import build_evidence
from .fees import classify_fee_label

logger = logging.getLogger("tinytravel.router")
IST = timezone(timedelta(hours=5, minutes=30))


async def run_own_playbook(
    platform: str,
    hotel_name: str,
    req: dict,
    *,
    timeout_s: float = 90.0,
    max_steps: int = 45,
    on_stream_url: Optional[Callable[[str], Any]] = None,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """
    Execute local deterministic Playwright playbook for Cleartrip or Agoda.
    Constructs full Offer dictionary with screenshot and page text evidence.
    """
    p = platform.lower().replace(".", "").replace(" ", "").replace("-", "")
    t0 = datetime.now(IST)
    started_at = t0.isoformat()

    hotel_slug = hotel_name.lower().replace(" ", "_")
    site_slug = p
    offer_id = req.get("offer_id") or f"off_{site_slug}_{hotel_slug[:8]}"
    hotel_id = req.get("hotel_id") or f"h_{hotel_slug[:8]}"

    req_copy = dict(req)
    req_copy["offer_id"] = offer_id
    req_copy["hotel_id"] = hotel_id

    if on_progress:
        try:
            await on_progress(f"Starting own Playwright playbook for {hotel_name} on {platform}...")
        except Exception:
            pass

    probe_data: Dict[str, Any] = {}
    if p == "cleartrip":
        try:
            from api.agents.playbooks.cleartrip import run_cleartrip_playbook
        except ImportError:
            from agents.playbooks.cleartrip import run_cleartrip_playbook
        probe_data = await run_cleartrip_playbook(hotel_name, req_copy, timeout_s=min(timeout_s, 90.0), max_steps=max_steps)
    elif p == "agoda":
        try:
            from api.agents.playbooks.agoda import run_agoda_playbook
        except ImportError:
            from agents.playbooks.agoda import run_agoda_playbook
        probe_data = await run_agoda_playbook(hotel_name, req_copy, timeout_s=min(timeout_s, 90.0), max_steps=max_steps)
    else:
        # Platform unsupported by own playbooks
        probe_data = {
            "site": platform,
            "status": "unverified",
            "blocker": "other",
            "notes": f"Platform '{platform}' has no local playbook implemented.",
            "steps": 0,
            "cost_usd": 0.0,
        }

    t1 = datetime.now(IST)
    finished_at = t1.isoformat()

    # Extract observed fields
    site = probe_data.get("site") or platform
    reached_payment_page = bool(probe_data.get("reached_payment_page", False))
    furthest_step = probe_data.get("furthest_step") or ("payment" if reached_payment_page else "unknown")
    blocker = probe_data.get("blocker")
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
    notes = probe_data.get("notes") or ""

    # Verify max_occupancy fits requested guests
    req_guests = int(req.get("guests", 2))
    max_occ = probe_data.get("max_occupancy")
    occupancy_mismatch = False
    if max_occ is not None and max_occ < req_guests:
        occupancy_mismatch = True
        notes = (notes + f" [Occupancy mismatch: room fits {max_occ} adults but search requested {req_guests}]").strip()

    c_cat = cancellation_category(policy)
    pay_now = probe_data.get("pay_now")
    pay_at_hotel = probe_data.get("pay_at_hotel")
    rate_cohort = probe_data.get("rate_cohort") or "cheapest_free_cancellation"
    cheapest_any_payable = probe_data.get("cheapest_any_payable")

    recon = reconciliation_status(fee_lines, price_payable, pay_now=pay_now, pay_at_hotel=pay_at_hotel)

    # Check for screenshot artifact in evidence/
    evidence_dir = Path(__file__).resolve().parents[2] / "evidence"
    shot_fn = f"{offer_id}_screenshot.png"
    screenshot_url = f"/evidence/{shot_fn}" if (evidence_dir / shot_fn).exists() else None

    evidence = build_evidence(
        streaming_url=None,
        listing_page_text=listing_page_text,
        payment_page_text=payment_page_text,
        price_shown_on_listing=price_listing,
        price_shown_on_room_selection=price_room,
        price_final_payable=price_payable,
        started_at=started_at,
        finished_at=finished_at,
        currency=currency,
        mock=False,
        existing_evidence=None,
        offer_id=offer_id,
        screenshot_url=screenshot_url,
    )

    status = determine_status(
        reached_payment_page=reached_payment_page,
        final_price=price_payable,
        evidence=evidence,
        reconciliation=recon,
        blocker=blocker,
        occupancy_mismatch=occupancy_mismatch,
        currency_mismatch=False,
    )

    leak = fee_leak_pct(price_listing, price_payable, same_room=True) if status == "verified" else None

    steps = int(probe_data.get("steps", 0))
    run_id = f"own_{offer_id}_{int(t0.timestamp())}"

    return {
        "offer_id": offer_id,
        "hotel_id": hotel_id,
        "run_id": run_id,
        "streaming_url": None,
        "started_at": started_at,
        "finished_at": finished_at,
        "steps": steps,
        "cost_usd": 0.0,
        "status": status,
        "reconciliation": recon,
        "cancellation_category": c_cat,
        "site": site,
        "reached_payment_page": reached_payment_page,
        "furthest_step": furthest_step,
        "blocker": blocker,
        "hotel_name": probe_data.get("hotel_name") or hotel_name,
        "hotel_url": probe_data.get("hotel_url") or "",
        "room_type": probe_data.get("room_type", ""),
        "max_occupancy": probe_data.get("max_occupancy", req_guests),
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
        "pay_now": pay_now,
        "pay_at_hotel": pay_at_hotel,
        "rate_cohort": rate_cohort,
        "cheapest_any_payable": cheapest_any_payable,
        "verification_level": probe_data.get("verification_level", "checkout"),
        "evidence": evidence,
        "mock": False,
        "listing_page_text": listing_page_text,
        "payment_page_text": payment_page_text,
        "transparency": (
            {"score": None, "breakdown": None, "note": "N/A (not verified)"}
            if status != "verified"
            else transparency_score({
                "status": status,
                "fee_leak_pct": leak,
                "preselected_addons": probe_data.get("preselected_addons", []),
                "urgency_or_scarcity_messages": probe_data.get("urgency_or_scarcity_messages", []),
                "evidence": evidence,
            })
        ),
    }


async def run_hybrid_agent(
    platform: str,
    hotel_name: str,
    req: dict,
    *,
    runner: Optional[str] = None,
    profile: str = "lite",
    timeout_s: float = 360.0,
    on_stream_url: Optional[Callable[[str], Any]] = None,
    on_progress: Optional[Callable[[str], Any]] = None,
) -> Dict[str, Any]:
    """
    Route checkout verification according to AGENT_RUNNER config (own|tinyfish|hybrid).
    Defaults to AGENT_RUNNER env var, falling back to 'hybrid'.
    """
    selected_runner = (runner or os.getenv("AGENT_RUNNER", "hybrid")).lower().strip()
    p = platform.lower().replace(".", "").replace(" ", "").replace("-", "")

    # Mode 1: own only
    if selected_runner == "own":
        logger.info("[AGENT_ROUTER] Runner='own' selected for %s on %s", hotel_name, platform)
        return await run_own_playbook(
            platform, hotel_name, req,
            timeout_s=min(timeout_s, 90.0),
            on_stream_url=on_stream_url,
            on_progress=on_progress,
        )

    # Mode 2: tinyfish only
    if selected_runner == "tinyfish":
        logger.info("[AGENT_ROUTER] Runner='tinyfish' selected for %s on %s", hotel_name, platform)
        try:
            from api.agents.checkout import verify_offer
        except ImportError:
            from agents.checkout import verify_offer
        return await verify_offer(
            platform, hotel_name, req,
            profile=profile,
            on_stream_url=on_stream_url,
            on_progress=on_progress,
            force_tinyfish=True,
        )

    # Mode 3: hybrid (own first for Cleartrip/Agoda, TinyFish fallback)
    if p in ("cleartrip", "agoda"):
        try:
            logger.info("[AGENT_ROUTER] Hybrid: Attempting own playbook first for %s on %s", hotel_name, platform)
            res = await run_own_playbook(
                platform, hotel_name, req,
                timeout_s=min(timeout_s, 90.0),
                on_stream_url=on_stream_url,
                on_progress=on_progress,
            )
            if res.get("status") == "verified":
                logger.info("[AGENT_ROUTER] Own playbook succeeded!")
                return res
            logger.warning(
                "[AGENT_ROUTER] Own playbook unverified/blocked (status=%s, blocker=%s). Falling back to TinyFish.",
                res.get("status"), res.get("blocker")
            )
        except Exception as e:
            logger.warning("[AGENT_ROUTER] Own playbook exception (%s). Falling back to TinyFish.", e)

    # Fallback to TinyFish
    try:
        from api.agents.checkout import verify_offer
    except ImportError:
        from agents.checkout import verify_offer
    return await verify_offer(
        platform, hotel_name, req,
        profile=profile,
        on_stream_url=on_stream_url,
        on_progress=on_progress,
        force_tinyfish=True,
    )
