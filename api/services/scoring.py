"""Pure scoring and verification functions. Golden-tested against fixtures/demo_run.json."""
from typing import Optional, Literal

Status = Literal["verified", "unverified", "blocked"]
CancelCategory = Literal["free", "partial", "non_refundable"]
Reconciliation = Literal["ok", "mismatch"]


def fee_leak_pct(listing: Optional[float], final: Optional[float]) -> Optional[float]:
    """Calculate fee leak percentage between listing price and final payable price."""
    if not listing or final is None:
        return None
    return round((final - listing) / listing * 100, 1)


def reconciles(fee_lines: Optional[list[dict]], final: Optional[float], tol: float = 0.01) -> bool:
    """Check if itemized fee lines sum to final payable price within tolerance."""
    if final is None or not fee_lines:
        return False
    return abs(sum(l["amount"] for l in fee_lines) - final) <= tol * final


def reconciliation_status(fee_lines: Optional[list[dict]], final: Optional[float], tol: float = 0.01) -> Optional[Reconciliation]:
    """Return 'ok', 'mismatch', or None if fee lines / final price are absent."""
    if final is None or not fee_lines:
        return None
    if reconciles(fee_lines, final, tol=tol):
        return "ok"
    return "mismatch"


def cancellation_category(policy_text: Optional[str]) -> Optional[CancelCategory]:
    """Classify free-text cancellation policy into free, partial, or non_refundable."""
    if not policy_text or not policy_text.strip():
        return None
    p = policy_text.lower()
    if "free cancellation" in p:
        return "free"
    if any(term in p for term in ["non-refundable", "non refundable", "no refund", "nonrefundable"]):
        return "non_refundable"
    return "partial"


def determine_status(
    reached_payment_page: bool,
    final_price: Optional[float],
    evidence: list,
    reconciliation: Optional[str],
    blocker: Optional[str] = None,
) -> Status:
    """Evaluate offer verification status by the strict TinyTravel product rules."""
    if blocker is not None:
        return "blocked"
    if (
        reached_payment_page
        and final_price is not None
        and len(evidence) > 0
        and reconciliation == "ok"
    ):
        return "verified"
    return "unverified"


def verified(o: dict) -> bool:
    """Check if offer dictionary meets all verified invariants."""
    return (
        bool(o.get("reached_payment_page"))
        and o.get("price_final_payable") is not None
        and len(o.get("evidence", [])) > 0
        and reconciles(o.get("fee_lines", []), o["price_final_payable"])
    )
