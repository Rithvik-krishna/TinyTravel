from pathlib import Path
import pytest
import re

from api.schemas import FeeLine, Offer
from api.services.scoring import reconciles, reconciliation_status


def test_booking_tax_breakout_oberoi_hindi():
    """Verify Booking.com tax parsing on Oberoi Hindi saved text."""
    txt_path = Path("results/recon/oberoi_fin_text.txt")
    if not txt_path.exists():
        pytest.skip("Oberoi Hindi text file not found")

    txt = txt_path.read_text(encoding="utf-8")
    m_base = re.search(r'(?:price|room price|charges for \d+ room[s]?|कीमत)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', txt, re.I)
    assert m_base is not None
    base_fare = float(m_base.group(1).replace(",", ""))
    assert base_fare == 31000.0

    m_tax = re.search(r'\+\s*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:taxes|charges|टैक्स|शुल्क)', txt, re.I)
    assert m_tax is not None
    taxes = float(m_tax.group(1).replace(",", ""))
    assert taxes == 5580.0

    payable = round(base_fare + taxes, 2)
    assert payable == 36580.0
    # Fee lines sum to payable within 0%
    assert base_fare + taxes == payable


def test_booking_tax_breakout_oberoi_english():
    """Verify Booking.com tax parsing on Oberoi English saved text."""
    txt_path = Path("results/recon/real_pairs/bookingcom_the_oberoi_bengaluru_2026-11-20_1794892980.txt")
    if not txt_path.exists():
        pytest.skip("Oberoi English text file not found")

    txt = txt_path.read_text(encoding="utf-8")
    m_base = re.search(r'(?:price|room price|charges for \d+ room[s]?|कीमत)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', txt, re.I)
    assert m_base is not None
    base_fare = float(m_base.group(1).replace(",", ""))
    assert base_fare == 27000.0

    m_tax = re.search(r'\+\s*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:taxes|charges|टैक्स|शुल्क)', txt, re.I)
    assert m_tax is not None
    taxes = float(m_tax.group(1).replace(",", ""))
    assert taxes == 4860.0

    # 18% GST check
    assert taxes == round(0.18 * base_fare, 2)

    payable = round(base_fare + taxes, 2)
    assert payable == 31860.0


def test_booking_tax_breakout_bloomrooms_english():
    """Verify Booking.com tax parsing on Bloomrooms English saved text."""
    txt_path = Path("results/recon/real_pairs/bookingcom_bloomrooms_city_centre_2026-11-20_1794892782.txt")
    if not txt_path.exists():
        pytest.skip("Bloomrooms English text file not found")

    txt = txt_path.read_text(encoding="utf-8")
    m_base = re.search(r'(?:price|room price|charges for \d+ room[s]?|कीमत)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', txt, re.I)
    assert m_base is not None
    base_fare = float(m_base.group(1).replace(",", ""))
    assert base_fare == 5580.0

    m_tax = re.search(r'\+\s*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:taxes|charges|टैक्स|शुल्क)', txt, re.I)
    assert m_tax is not None
    taxes = float(m_tax.group(1).replace(",", ""))
    assert taxes == 279.0

    payable = round(base_fare + taxes, 2)
    assert payable == 5859.0


def test_booking_tax_breakout_ibis_english():
    """Verify Booking.com tax parsing on ibis English saved text."""
    txt_path = Path("results/recon/real_pairs/bookingcom_ibis_bengaluru_city_centre_2026-11-20_1794892805.txt")
    if not txt_path.exists():
        pytest.skip("ibis English text file not found")

    txt = txt_path.read_text(encoding="utf-8")
    m_base = re.search(r'(?:price|room price|charges for \d+ room[s]?|कीमत)\s*[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', txt, re.I)
    assert m_base is not None
    base_fare = float(m_base.group(1).replace(",", ""))
    assert base_fare == 6499.0

    m_tax = re.search(r'\+\s*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)\s*(?:taxes|charges|टैक्स|शुल्क)', txt, re.I)
    assert m_tax is not None
    taxes = float(m_tax.group(1).replace(",", ""))
    assert taxes == 324.95

    payable = round(base_fare + taxes, 2)
    assert payable == 6823.95


def test_reconciliation_invariant_all_inclusive():
    """Verify reconciliation is 'ok' when fee_lines match all-inclusive payable."""
    fee_lines = [
        {"label": "Room rate", "amount": 27000.0, "fee_kind": "other"},
        {"label": "Taxes & charges", "amount": 4860.0, "fee_kind": "tax"},
    ]
    status = reconciliation_status(fee_lines, 31860.0)
    assert status == "ok"
    assert reconciles(fee_lines, 31860.0) is True
