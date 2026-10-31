"""Handoff pack construction service.
Builds ready-to-pay handoff package with deep link, QR code, selection card, and dummy guest details.
"""
import base64
from datetime import datetime, timezone, timedelta
import io
from typing import Optional
import qrcode

try:
    from ..models import HandoffPack, SelectionCard, CopyPastePack
except ImportError:
    from models import HandoffPack, SelectionCard, CopyPastePack

IST = timezone(timedelta(hours=5, minutes=30))


def generate_qr_base64(url: str) -> str:
    """Generate a base64-encoded PNG data string of the given URL."""
    if not url:
        return ""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _format_time_label(iso_timestamp: Optional[str]) -> str:
    """Format ISO timestamp into human readable 12-hour time (e.g. '10:13 PM')."""
    if not iso_timestamp:
        return datetime.now(IST).strftime("%I:%M %p")
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.astimezone(IST).strftime("%I:%M %p")
    except Exception:
        return datetime.now(IST).strftime("%I:%M %p")


def _format_dates_label(req_dict: Optional[dict]) -> str:
    """Format check-in and check-out dates into a clean label."""
    if not req_dict:
        return "20-21 Nov 2026 (1 night)"
    ci = req_dict.get("check_in", "2026-11-20")
    co = req_dict.get("check_out", "2026-11-21")
    try:
        d1 = datetime.fromisoformat(ci)
        d2 = datetime.fromisoformat(co)
        nights = max(1, (d2 - d1).days)
        s1 = d1.strftime("%d")
        s2 = d2.strftime("%d %b %Y")
        return f"{s1}-{s2} ({nights} night{'s' if nights > 1 else ''})"
    except Exception:
        return f"{ci} to {co}"


def build_handoff(offer: dict, req: Optional[dict] = None) -> dict:
    """Build a contract-compliant HandoffPack for the given offer."""
    offer_id = offer.get("offer_id", "unknown_offer")
    platform = offer.get("site") or "Cleartrip"
    hotel_name = offer.get("hotel_name") or "Selected Hotel"
    deep_link = offer.get("hotel_url") or "https://www.cleartrip.com"
    currency = offer.get("currency") or "INR"

    is_mock = bool(offer.get("mock", False))
    verified_at = offer.get("finished_at") or offer.get("started_at") or datetime.now(IST).isoformat()
    time_label = _format_time_label(verified_at)
    dates_label = _format_dates_label(req)

    # Determine cancellation label
    c_cat = offer.get("cancellation_category")
    raw_policy = offer.get("cancellation_policy") or ""
    if raw_policy:
        cancellation_label = raw_policy
    elif c_cat == "free":
        cancellation_label = "Free cancellation"
    elif c_cat == "non_refundable":
        cancellation_label = "Non-refundable"
    else:
        cancellation_label = "Partial cancellation"

    qr_b64 = generate_qr_base64(deep_link)

    pack_data = {
        "offer_id": offer_id,
        "platform": platform,
        "deep_link": deep_link,
        "qr_png_base64": qr_b64,
        "qr_note": f"Scan on mobile to pay directly on {platform}",
        "selection_card": {
            "hotel": hotel_name,
            "room_type": offer.get("room_type") or "Standard Room",
            "meal_plan": offer.get("meal_plan") or "Room Only",
            "cancellation": cancellation_label,
            "dates": dates_label,
            "guests": int(offer.get("max_occupancy") or (req.get("guests") if req else 2) or 2),
            "expected_final_payable": offer.get("price_final_payable"),
            "currency": currency,
            "verified_at": verified_at,
        },
        "copy_paste": {
            "name": "Test Guest",
            "email": "test.guest+probe@example.com",
            "phone": "9000000000",
        },
        "disclaimer": f"Price verified at {time_label}. Re-check before paying; prices can change.",
        "mock": is_mock,
    }

    # Validate against Pydantic schema
    validated = HandoffPack.model_validate(pack_data)
    return validated.model_dump()
