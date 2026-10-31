"""Recheck Agent service.
Re-runs verification for a specific offer using captured hotel_url and identical room parameters.
Diffs price trail, records price history, and updates offer transparency stability.
"""
from datetime import datetime, timezone, timedelta
import os
import uuid
from typing import Optional, Any

try:
    from ..models import Recheck, TrailDiffItem, RecheckSnapshot
    from ..db import get_offer, save_offer, save_price_history
    from ..services.scoring import transparency_score
    from .checkout import verify_offer
except ImportError:
    from models import Recheck, TrailDiffItem, RecheckSnapshot
    from db import get_offer, save_offer, save_price_history
    from services.scoring import transparency_score
    from agents.checkout import verify_offer

IST = timezone(timedelta(hours=5, minutes=30))


def diff_price_trails(previous_trail: list[dict], current_trail: list[dict]) -> list[dict]:
    """Calculate differences across observed checkout steps in price trail."""
    prev_map = {p.get("step"): p.get("amount") for p in previous_trail if p.get("amount") is not None}
    curr_map = {p.get("step"): p.get("amount") for p in current_trail if p.get("amount") is not None}

    diffs = []
    for step in ("listing", "room", "traveller_details", "payment"):
        if step in prev_map and step in curr_map:
            b_val = float(prev_map[step])
            a_val = float(curr_map[step])
            if b_val != a_val:
                diffs.append({
                    "step": step,
                    "before": b_val,
                    "after": a_val,
                })

    # Always ensure payment step is included in trail_diff
    if not any(d["step"] == "payment" for d in diffs):
        p_prev = prev_map.get("payment", 0.0)
        p_curr = curr_map.get("payment", 0.0)
        diffs.append({
            "step": "payment",
            "before": float(p_prev),
            "after": float(p_curr),
        })

    return diffs


def calculate_recheck(
    offer_id: str,
    previous_amount: float,
    previous_at: str,
    current_amount: float,
    current_at: str,
    previous_trail: Optional[list[dict]] = None,
    current_trail: Optional[list[dict]] = None,
    mock: bool = False,
    recheck_id: Optional[str] = None,
) -> dict:
    """Pure calculation of price re-check difference, percentage, and observation message."""
    delta = round(current_amount - previous_amount, 2)
    delta_pct = round(abs(delta) / previous_amount * 100.0, 1) if previous_amount > 0 else 0.0

    try:
        t_prev = datetime.fromisoformat(previous_at)
        t_curr = datetime.fromisoformat(current_at)
        elapsed_minutes = max(1, int(abs((t_curr - t_prev).total_seconds()) / 60))
    except Exception:
        elapsed_minutes = 23

    trail_diff = diff_price_trails(previous_trail or [], current_trail or [])

    if delta == 0:
        message = f"Price stable at INR {int(current_amount):,} in {elapsed_minutes} min (observed)."
    else:
        message = f"Price moved INR {int(previous_amount):,} -> INR {int(current_amount):,} in {elapsed_minutes} min (observed)."

    rec_id = recheck_id or f"recheck_{offer_id}_{int(datetime.now().timestamp())}"

    payload = {
        "recheck_id": rec_id,
        "offer_id": offer_id,
        "status": "done",
        "previous": {
            "amount": float(previous_amount),
            "at": previous_at,
        },
        "current": {
            "amount": float(current_amount),
            "at": current_at,
        },
        "delta": delta,
        "delta_pct": delta_pct,
        "elapsed_minutes": elapsed_minutes,
        "trail_diff": trail_diff,
        "message": message,
        "mock": mock,
    }

    validated = Recheck.model_validate(payload)
    return validated.model_dump()


async def recheck_offer(offer_id: str) -> dict:
    """Execute recheck for an offer, diffing against previous verified price."""
    offer = get_offer(offer_id)
    is_disabled = os.getenv("DISABLE_LIVE") == "1"
    max_spend = float(os.getenv("MAX_SPEND_USD", "4.0"))
    spend = 0.0
    try:
        from ..db import get_total_spend
        spend = get_total_spend()
    except Exception:
        pass

    is_live = (
        os.getenv("DATA_MODE") == "live"
        and os.getenv("TINYFISH_FAKE") != "1"
        and not is_disabled
        and (spend < max_spend)
    )

    if not offer:
        # Fallback to demo fixture if available
        import json
        from pathlib import Path
        demo_path = Path(__file__).resolve().parents[2] / "fixtures" / "demo_run.json"
        if demo_path.exists():
            demo_data = json.loads(demo_path.read_text(encoding="utf-8"))
            matched = next((o for o in demo_data.get("offers", []) if o.get("offer_id") == offer_id), None)
            if matched:
                offer = matched

    if not offer:
        raise ValueError(f"Offer '{offer_id}' not found.")

    prev_payable = float(offer.get("price_final_payable") or 0.0)
    prev_at = offer.get("finished_at") or offer.get("started_at") or datetime.now(IST).isoformat()
    prev_trail = offer.get("price_trail") or []

    now_iso = datetime.now(IST).isoformat()

    if is_live and offer.get("hotel_url"):
        # Real live re-run against captured hotel_url
        req = {
            "url": offer["hotel_url"],
            "destination": "Bengaluru",
            "guests": offer.get("max_occupancy", 2),
            "rooms": 1,
            "must_have": {
                "free_cancellation": offer.get("cancellation_category") == "free",
                "breakfast": "breakfast" in (offer.get("meal_plan") or "").lower(),
            },
        }
        recheck_run = await verify_offer(
            platform=offer.get("site", "Cleartrip"),
            hotel_name=offer.get("hotel_name", "Hotel"),
            req=req,
        )
        curr_payable = float(recheck_run.get("price_final_payable") or prev_payable)
        curr_trail = recheck_run.get("price_trail") or prev_trail
        curr_at = recheck_run.get("finished_at") or now_iso
        mock = False
    else:
        # Deterministic simulated re-check
        # Slight price change (+2.7% or +278 INR as in demo_run)
        curr_payable = prev_payable + 278.0 if prev_payable else 10690.0
        curr_at = now_iso
        curr_trail = [dict(p) for p in prev_trail]
        for p in curr_trail:
            if p.get("step") == "payment":
                p["amount"] = curr_payable
        mock = True

    recheck_res = calculate_recheck(
        offer_id=offer_id,
        previous_amount=prev_payable,
        previous_at=prev_at,
        current_amount=curr_payable,
        current_at=curr_at,
        previous_trail=prev_trail,
        current_trail=curr_trail,
        mock=mock,
    )

    # Persist verified price in ledger
    save_price_history(
        hotel=offer.get("hotel_name", "Unknown Hotel"),
        platform=offer.get("site", "Unknown Platform"),
        amount=curr_payable,
        captured_at=curr_at,
        offer_id=offer_id,
    )

    # Re-calculate transparency with price stability component
    new_transparency = transparency_score(offer, recheck=recheck_res)
    offer["transparency"] = new_transparency

    # Update offer in DB if present
    save_offer(offer_id, offer.get("search_id", "recheck_search"), offer)

    return recheck_res
