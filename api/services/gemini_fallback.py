"""
Gemini Extraction Fallback Service.
Activated when GEMINI_FALLBACK_EXTRACTION=true and GEMINI_API_KEY is configured.
Never exposes or logs secret keys.
Gracefully falls back to deterministic extraction if disabled or unavailable.
"""
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import re
import ssl
from typing import Dict, Any, Optional
import urllib.request

logger = logging.getLogger("tinytravel.gemini_fallback")
IST = timezone(timedelta(hours=5, minutes=30))


def is_gemini_fallback_enabled() -> bool:
    """Check if Gemini extraction fallback is enabled via environment variable."""
    val = os.getenv("GEMINI_FALLBACK_EXTRACTION", "false").strip().lower()
    return val in ("true", "1", "yes", "on")


def extract_with_gemini_fallback(
    page_text: str,
    hotel_name: str = "",
    site: str = "",
) -> Optional[Dict[str, Any]]:
    """Use Gemini LLM to extract structured pricing and breakdown from raw page text.

    Returns dict matching schema:
    {
        "price_final_payable": float or None,
        "fee_lines": list of {"label": str, "amount": float, "fee_kind": str},
        "room_type": str or None,
        "meal_plan": str or None,
        "cancellation_policy": str or None,
    }
    or None if disabled, failed, or key missing.
    """
    if not is_gemini_fallback_enabled():
        return None

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.debug("GEMINI_FALLBACK_EXTRACTION is enabled but GEMINI_API_KEY is not configured.")
        return None

    model_name = os.getenv("GEMINI_EXTRACTION_MODEL", "gemini-1.5-flash")
    prompt = (
        f"You are a travel pricing extraction system. Analyze the following checkout page text for {hotel_name} on {site}.\n"
        "Extract the exact numbers and policy terms present in the text into this JSON format:\n"
        "{\n"
        '  "price_final_payable": float or null,\n'
        '  "fee_lines": [\n'
        '    {"label": str, "amount": float, "fee_kind": "tax" | "platform_fee" | "property_fee" | "add_on" | "other"}\n'
        "  ],\n"
        '  "room_type": str or null,\n'
        '  "meal_plan": str or null,\n'
        '  "cancellation_policy": str or null\n'
        "}\n"
        "Rules:\n"
        "- Never fabricate numbers. If not mentioned in the text, use null.\n"
        "- Amounts must be in INR numbers without commas or currency symbols.\n"
        "- Return ONLY the JSON object without code fences."
    )

    # Truncate text to avoid token limits
    snippet = page_text[:8000]

    req_data = {
        "contents": [
            {
                "parts": [
                    {"text": f"{prompt}\n\nPAGE_TEXT:\n{snippet}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json"
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(req_data).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )

    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            candidates = res_json.get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            raw_text_out = "".join(p.get("text", "") for p in parts)
            match = re.search(r"\{.*\}", raw_text_out, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                # Validate and sanitize fields
                payable = data.get("price_final_payable")
                fee_lines = data.get("fee_lines") or []
                clean_lines = []
                for fl in fee_lines:
                    if isinstance(fl, dict) and "amount" in fl and "label" in fl:
                        clean_lines.append({
                            "label": str(fl["label"]),
                            "amount": float(fl["amount"]),
                            "fee_kind": str(fl.get("fee_kind", "other")),
                        })
                return {
                    "price_final_payable": float(payable) if payable is not None else None,
                    "fee_lines": clean_lines,
                    "room_type": data.get("room_type"),
                    "meal_plan": data.get("meal_plan"),
                    "cancellation_policy": data.get("cancellation_policy"),
                    "extracted_by": "gemini_fallback",
                }
    except Exception as e:
        logger.warning("Gemini extraction fallback call failed: %s", e)
        return None

    return None
