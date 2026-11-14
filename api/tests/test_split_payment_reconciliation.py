"""
Unit tests for split payment parsing and fee reconciliation.
"""
from api.services.scoring import reconciles, reconciliation_status


def test_reconciles_standard_fee_lines():
    fee_lines = [
        {"label": "Room (1 night)", "amount": 10000.0},
        {"label": "GST 18%", "amount": 1800.0},
        {"label": "Convenience fee", "amount": 500.0},
    ]
    final_price = 12300.0
    assert reconciles(fee_lines, final_price) is True
    assert reconciliation_status(fee_lines, final_price) == "ok"


def test_reconciles_split_payment():
    # Split payment: Pay now to OTA + Pay later at hotel
    # e.g., Agoda model: Pay online Rs 18,530.72 + Pay at property Rs 2,128.56 = Rs 20,659.28
    pay_now = 18530.72
    pay_at_hotel = 2128.56
    final_payable = 20659.28

    # fee_lines could be empty or omit property taxes
    empty_lines = []
    assert reconciles(empty_lines, final_payable, pay_now=pay_now, pay_at_hotel=pay_at_hotel) is True
    assert reconciliation_status(empty_lines, final_payable, pay_now=pay_now, pay_at_hotel=pay_at_hotel) == "ok"


def test_reconciles_split_payment_mismatch():
    pay_now = 18000.0
    pay_at_hotel = 2000.0
    final_payable = 20659.28  # 20,000 != 20,659.28

    assert reconciles([], final_payable, pay_now=pay_now, pay_at_hotel=pay_at_hotel) is False
    assert reconciliation_status([], final_payable, pay_now=pay_now, pay_at_hotel=pay_at_hotel) == "mismatch"
