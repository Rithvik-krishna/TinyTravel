import pytest
from pathlib import Path
from api.services.dual_extraction import parse_dom_payment_text, validate_extraction_invariants

ROOT = Path(__file__).resolve().parents[2]
REAL_PAIRS = ROOT / "results" / "recon" / "real_pairs"

def old_buggy_booking_parser(text: str) -> float:
    """The legacy buggy parser prior to the tax audit.
    
    Bugs:
    1. Regex `(?:price|total)` matched 'Price: 5580' first and dropped statutory taxes and charges.
    2. Matched 'Original price: 9000', missed the Genius discount, adding taxes to the wrong base or omitting discount.
    """
    import re
    # Legacy buggy regex: stopped at first 'price' or 'total' match without breakout
    m = re.search(r'(?:price|total|amount)[\s:]*[₹Rs.\s]*([0-9,]+)', text, re.I)
    return float(m.group(1).replace(",", "")) if m else 0.0

# Golden Files and their mathematically verified ground truth
GOLDEN_CASES = [
    {
        "name": "Radisson Blu 2026-11-20 (Discounted Base + 18% GST)",
        "file": REAL_PAIRS / "bookingcom_radisson_blu_atria_bengaluru_2026-11-20_1794895333.txt",
        "expected_base": 8100.0,
        "expected_discount": 900.0,
        "expected_taxes": 1458.0,
        "expected_total": 9558.0,
        "expected_gst_slab": "18%",
        "old_buggy_total": 9000.0,  # Old parser extracted Original price 9,000 and dropped tax/discount
    },
    {
        "name": "Radisson Blu 2026-11-27 (Discounted Base + 18% GST)",
        "file": REAL_PAIRS / "bookingcom_radisson_blu_atria_bengaluru_2026-11-27_1794895394.txt",
        "expected_base": 10710.0,
        "expected_discount": 1190.0,
        "expected_taxes": 1927.80,
        "expected_total": 12637.80,
        "expected_gst_slab": "18%",
        "old_buggy_total": 11900.0,
    },
    {
        "name": "Bloomrooms City Centre 2026-11-20 (Universal Base + 5% GST)",
        "file": REAL_PAIRS / "bookingcom_bloomrooms_city_centre_2026-11-20_1794895236.txt",
        "expected_base": 5580.0,
        "expected_discount": 0.0,
        "expected_taxes": 279.0,
        "expected_total": 5859.0,
        "expected_gst_slab": "5%",
        "old_buggy_total": 5580.0,  # Old parser dropped ₹279 tax
    },
    {
        "name": "The Oberoi Bengaluru 2026-11-20 (Universal Base + 18% GST)",
        "file": REAL_PAIRS / "bookingcom_the_oberoi_bengaluru_2026-11-20_1794895532.txt",
        "expected_base": 27000.0,
        "expected_discount": 0.0,
        "expected_taxes": 4860.0,
        "expected_total": 31860.0,
        "expected_gst_slab": "18%",
        "old_buggy_total": 27000.0,  # Old parser dropped ₹4,860 tax
    },
    {
        "name": "ibis Bengaluru City Centre 2026-11-20 (Universal Base + 5% GST)",
        "file": REAL_PAIRS / "bookingcom_ibis_bengaluru_city_centre_2026-11-20_1794895669.txt",
        "expected_base": 6499.0,
        "expected_discount": 0.0,
        "expected_taxes": 324.95,
        "expected_total": 6823.95,
        "expected_gst_slab": "5%",
        "old_buggy_total": 6499.0,  # Old parser dropped ₹324.95 tax
    },
]

@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_golden_pages_new_parser(case):
    """Verify that new parser correctly parses base, discounts, taxes, and totals from golden pages."""
    filepath = case["file"]
    assert filepath.exists(), f"Golden file {filepath} must exist"
    
    text = filepath.read_text(encoding="utf-8")
    parsed = parse_dom_payment_text(text)
    
    # 1. Assert exact total
    assert abs(parsed["total_payable"] - case["expected_total"]) <= 0.01, (
        f"[{case['name']}] Expected total {case['expected_total']}, got {parsed['total_payable']}"
    )
    
    # 2. Assert exact taxes
    assert abs(parsed["taxes"] - case["expected_taxes"]) <= 0.01, (
        f"[{case['name']}] Expected taxes {case['expected_taxes']}, got {parsed['taxes']}"
    )
    
    # 3. Assert invariants (reconciliation and GST slab)
    validation = validate_extraction_invariants(parsed)
    assert validation["invariants_passed"] is True, f"Invariants failed: {validation['notes']}"
    assert validation["reconciliation"] == "ok"
    assert case["expected_gst_slab"] in (validation["gst_slab"] or "")

@pytest.mark.parametrize("case", GOLDEN_CASES)
def test_golden_pages_old_buggy_parser_fails(case):
    """Verify that the old buggy parser FAILS on every golden page, proving regression defense."""
    filepath = case["file"]
    text = filepath.read_text(encoding="utf-8")
    old_val = old_buggy_booking_parser(text)
    
    # Prove that old parser failed to extract the true all-inclusive payable
    assert abs(old_val - case["expected_total"]) > 1.0, (
        f"[{case['name']}] Old parser should have failed! Extracted {old_val} matching expected {case['expected_total']}"
    )
    assert old_val == case["old_buggy_total"], (
        f"[{case['name']}] Old parser expected to reproduce bug value {case['old_buggy_total']}, got {old_val}"
    )
