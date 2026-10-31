"""Evidence construction service.
Builds verifiable evidence items from browser recordings, streaming URLs, and page text snippets.
Never fabricates or invents evidence URLs.
"""
from typing import Optional


def build_evidence(
    streaming_url: Optional[str] = None,
    listing_page_text: Optional[str] = None,
    payment_page_text: Optional[str] = None,
    price_shown_on_listing: Optional[float] = None,
    price_shown_on_room_selection: Optional[float] = None,
    price_final_payable: Optional[float] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    currency: str = "INR",
    mock: bool = False,
    existing_evidence: Optional[list[dict]] = None,
    offer_id: Optional[str] = None,
) -> list[dict]:

    """Construct evidence items adhering to TinyTravel invariants.

    Captures artifacts (text snippets, streaming links, screenshots) under /evidence/
    and points evidence URLs to the static /evidence/... endpoint.
    """
    if existing_evidence:
        return existing_evidence

    evidence_items = []
    timestamp = finished_at or started_at or ""
    
    from pathlib import Path
    evidence_dir = Path(__file__).resolve().parents[2] / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # Live session recording / stream URL
    if streaming_url:
        evidence_items.append({
            "type": "recording",
            "url": streaming_url,
            "step": "payment" if price_final_payable is not None else "listing",
            "captured_at": timestamp,
            "extracted_value": price_final_payable,
            "currency": currency,
            "mock": mock,
        })

    # Verifiable text excerpt from listing page
    if listing_page_text:
        listing_url = streaming_url or ""
        if offer_id:
            try:
                fn = f"{offer_id}_listing.txt"
                (evidence_dir / fn).write_text(listing_page_text, encoding="utf-8")
                listing_url = f"/evidence/{fn}"
            except Exception:
                pass
        evidence_items.append({
            "type": "page_text",
            "url": listing_url,
            "step": "listing",
            "captured_at": started_at or timestamp,
            "extracted_value": price_shown_on_listing,
            "currency": currency,
            "mock": mock,
        })

    # Verifiable text excerpt from payment page
    if payment_page_text:
        payment_url = streaming_url or ""
        if offer_id:
            try:
                fn = f"{offer_id}_payment.txt"
                (evidence_dir / fn).write_text(payment_page_text, encoding="utf-8")
                payment_url = f"/evidence/{fn}"
            except Exception:
                pass
        evidence_items.append({
            "type": "page_text",
            "url": payment_url,
            "step": "payment",
            "captured_at": finished_at or timestamp,
            "extracted_value": price_final_payable,
            "currency": currency,
            "mock": mock,
        })

    return evidence_items

