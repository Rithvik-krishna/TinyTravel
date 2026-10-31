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
) -> list[dict]:
    """Construct evidence items adhering to TinyTravel invariants.

    Until live screenshots are confirmed by the SDK, evidence consists of:
    - Live browser streaming link (type: 'recording')
    - Verifiable page text snippets (type: 'page_text')
    """
    if existing_evidence:
        return existing_evidence

    evidence_items = []
    timestamp = finished_at or started_at or ""

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
        evidence_items.append({
            "type": "page_text",
            "url": streaming_url or "",
            "step": "listing",
            "captured_at": started_at or timestamp,
            "extracted_value": price_shown_on_listing,
            "currency": currency,
            "mock": mock,
        })

    # Verifiable text excerpt from payment page
    if payment_page_text:
        evidence_items.append({
            "type": "page_text",
            "url": streaming_url or "",
            "step": "payment",
            "captured_at": finished_at or timestamp,
            "extracted_value": price_final_payable,
            "currency": currency,
            "mock": mock,
        })

    return evidence_items
