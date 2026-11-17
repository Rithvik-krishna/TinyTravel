import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("tinytravel.dual_extraction")

# Configurable GST Slab Table for Indian Hotel Accommodation
# Tariff brackets and permitted tax percentages
GST_SLABS = [
    {"name": "Exempt / Zero", "min_tariff": 0.0, "max_tariff": 1000.0, "expected_rates": [0.0]},
    {"name": "Budget / Concession", "min_tariff": 1000.01, "max_tariff": 7500.0, "expected_rates": [0.05, 0.12]},
    {"name": "Luxury / Premium", "min_tariff": 7500.01, "max_tariff": 1000000.0, "expected_rates": [0.18]},
]

def verify_gst_slab(discounted_base: float, taxes: float) -> Tuple[bool, Optional[str], Optional[float]]:
    """Verify that effective tax rate (taxes / discounted_base) matches an official GST slab."""
    if discounted_base <= 0:
        return False, None, None
    
    eff_rate = round(taxes / discounted_base, 4)
    
    matching_bracket = None
    for slab in GST_SLABS:
        if slab["min_tariff"] <= discounted_base <= slab["max_tariff"]:
            matching_bracket = slab
            break
            
    if not matching_bracket:
        matching_bracket = GST_SLABS[-1]
        
    for rate in matching_bracket["expected_rates"]:
        # Allow +/- 1.5% absolute variance for rounding or local municipal surcharge
        if abs(eff_rate - rate) <= 0.015:
            return True, f"{int(rate * 100)}%", eff_rate
            
    # Also check other slabs in case of transitional rating
    for slab in GST_SLABS:
        for rate in slab["expected_rates"]:
            if abs(eff_rate - rate) <= 0.015:
                return True, f"{int(rate * 100)}% ({slab['name']})", eff_rate
                
    return False, None, eff_rate

def parse_dom_payment_text(text: str) -> Dict[str, Any]:
    """Pure DOM text extraction for base, discount, taxes, fees, and total payable."""
    m_orig = re.search(r'(?:Original price|1 room x \d+ night)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', text, re.I)
    m_disc = re.search(r'(?:Genius discount|Property discount|Coupon discount[^\n\r:]*)[:\n\r\s]*([-\u2212]\s*[₹Rs.\s]*[0-9,]+(?:\.[0-9]+)?)', text, re.I)
    if not m_disc:
        m_disc = re.search(r'([-\u2212]\s*[₹Rs.\s]*[0-9,]+(?:\.[0-9]+)?)', text)
    
    m_price = re.search(r'(?:^|\n)\s*Price\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', text, re.I)
    
    orig = float(m_orig.group(1).replace(",", "")) if m_orig else None
    disc_val = 0.0
    if m_disc:
        clean_d = re.sub(r'[-\u2212₹Rs.\s]', '', m_disc.group(1))
        if clean_d:
            try:
                disc_val = float(clean_d)
            except ValueError:
                disc_val = 0.0
                
    if m_price:
        base_discounted = float(m_price.group(1).replace(",", ""))
    elif orig is not None:
        base_discounted = round(orig - disc_val, 2)
    else:
        m_b = re.search(r'(?:room price|room rate|charges for \d+ room[s]?|कीमत)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', text, re.I)
        base_discounted = float(m_b.group(1).replace(",", "")) if m_b else None

    # Taxes & charges
    m_tax = re.search(r'\+\s*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:taxes|charges)', text, re.I)
    if not m_tax:
        m_tax = re.search(r'(?:taxes\s*(?:and|&)?\s*(?:charges|fees)?|gst|hotel taxes|goods & services tax)[:\n\r\s]*[+₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', text, re.I)
    taxes = float(m_tax.group(1).replace(",", "")) if m_tax else 0.0

    # Total / Payable
    m_tot = re.search(r'(?:total\s*(?:amount|price|payable)?|amount payable|today you\'ll pay|you pay|cancellation cost|From \d\d:\d\d on)[:\n\r\s\w]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', text, re.I)
    tot = float(m_tot.group(1).replace(",", "")) if m_tot else None
    
    if tot is None and base_discounted is not None:
        tot = round(base_discounted + taxes, 2)
        
    return {
        "original_price": orig,
        "discount": disc_val,
        "discounted_base": base_discounted,
        "taxes": taxes,
        "fees": 0.0,
        "total_payable": tot
    }

async def extract_via_gemini_vision(screenshot_path: Path) -> Optional[Dict[str, Any]]:
    """Optional vision extraction behind ENABLE_GEMINI_VISION flag."""
    if not os.getenv("ENABLE_GEMINI_VISION", "0").lower() in ("1", "true", "yes"):
        return None
    if not screenshot_path.exists():
        return None
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.info("ENABLE_GEMINI_VISION is set but GEMINI_API_KEY is not configured; skipping vision.")
        return None
        
    try:
        # Use google-genai or fallback
        from google import genai
        client = genai.Client(api_key=api_key)
        img_bytes = screenshot_path.read_bytes()
        prompt = (
            "Analyze this hotel payment page screenshot. Extract in JSON format only: "
            '{"base_fare": float, "discount": float, "taxes": float, "fees": float, "total_payable": float}. '
            "Output valid JSON without formatting or markdown codeblocks."
        )
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, genai.types.Part.from_bytes(data=img_bytes, mime_type='image/png')]
        )
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return {
            "discounted_base": float(data.get("base_fare", 0.0)),
            "taxes": float(data.get("taxes", 0.0)),
            "fees": float(data.get("fees", 0.0)),
            "total_payable": float(data.get("total_payable", 0.0)),
        }
    except Exception as exc:
        logger.warning("Gemini vision extraction failed or unavailable: %s", exc)
        return None

def validate_extraction_invariants(
    dom_result: Dict[str, Any],
    vision_result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Assert invariants:
    1. base - discounts + taxes + fees = total (within 1%)
    2. tax / discounted_base vs GST slab table
    3. Dual extraction: accept only if DOM and Vision within 1%
    """
    out = {
        "verified": True,
        "reconciliation": "ok",
        "invariants_passed": True,
        "gst_slab": None,
        "effective_tax_rate": None,
        "notes": []
    }
    
    base = dom_result.get("discounted_base") or 0.0
    taxes = dom_result.get("taxes") or 0.0
    fees = dom_result.get("fees") or 0.0
    total = dom_result.get("total_payable") or 0.0
    
    # 1. Reconciliation invariant: base + taxes + fees == total within 1%
    expected_total = round(base + taxes + fees, 2)
    if total > 0:
        diff_pct = abs(expected_total - total) / total
        if diff_pct > 0.01:
            out["verified"] = False
            out["reconciliation"] = "mismatch"
            out["invariants_passed"] = False
            out["notes"].append(f"Fee lines mismatch: base+tax+fees={expected_total} vs total={total} ({diff_pct*100:.2f}%)")
    else:
        out["verified"] = False
        out["reconciliation"] = "unverified"
        out["notes"].append("Total payable is zero or missing")

    # 2. GST Slab table verification
    gst_ok, slab_name, eff_rate = verify_gst_slab(base, taxes)
    out["gst_slab"] = slab_name
    out["effective_tax_rate"] = eff_rate
    if not gst_ok and base > 0:
        out["notes"].append(f"Effective tax rate {eff_rate*100:.1f}% does not align with official GST slabs (5%, 12%, 18%)")

    # 3. Dual extraction cross-check (if vision active)
    if vision_result is not None:
        vis_total = vision_result.get("total_payable", 0.0)
        if vis_total > 0 and total > 0:
            v_diff = abs(total - vis_total) / total
            if v_diff > 0.01:
                out["verified"] = False
                out["invariants_passed"] = False
                out["notes"].append(f"Dual extraction conflict: DOM={total} vs Vision={vis_total} ({v_diff*100:.2f}%)")
            else:
                out["notes"].append(f"Dual extraction confirmed: DOM {total} == Vision {vis_total}")
                
    return out
