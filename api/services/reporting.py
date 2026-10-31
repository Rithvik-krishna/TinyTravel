"""Reporting module for TinyTravel.
Generates self-contained printable HTML evidence reports and polite fee inquiry drafts.
"""
from datetime import datetime
import html
from typing import Optional


SAFETY_STATEMENT = (
    "Guest-only verification with dummy details (Test Guest, test.guest+probe@example.com, 9000000000). "
    "Stopped at payment page; never paid, logged in, entered OTP, or completed transactions."
)


def generate_html_report(results: dict, search_id: Optional[str] = None) -> str:
    """Generate a self-contained, printable HTML evidence report with zero external assets."""
    sid = search_id or results.get("search_request", {}).get("raw_text") or "N/A"
    req = results.get("search_request", {})
    verdicts = results.get("verdicts", {})
    offers = results.get("offers", [])
    summary = results.get("summary_strip", {})

    destination = html.escape(str(req.get("destination", "N/A")))
    check_in = html.escape(str(req.get("check_in", "N/A")))
    check_out = html.escape(str(req.get("check_out", "N/A")))
    guests = html.escape(str(req.get("guests", 2)))
    rooms = html.escape(str(req.get("rooms", 1)))
    deal_mode = html.escape(str(verdicts.get("deal_mode", "best_value")).replace("_", " ").title())
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")

    # Overall headlines
    headlines = verdicts.get("overall", {}).get("headlines", {})
    cheapest_hl = html.escape(str(headlines.get("cheapest_verified", "N/A")))
    safe_hl = html.escape(str(headlines.get("safe_cheapest", "N/A")))
    best_hl = html.escape(str(headlines.get("best_for_you", "N/A")))

    # Summary strip stats
    listings_found = summary.get("listings_found", 0)
    unique_hotels = summary.get("unique_hotels", 0)
    verified_count = summary.get("verified", 0)
    blocked_count = summary.get("blocked", 0)
    avg_leak = summary.get("avg_fee_leak_pct")
    avg_leak_str = f"{avg_leak:.1f}%" if avg_leak is not None else "N/A"

    offers_html = []
    for off in offers:
        oid = html.escape(str(off.get("offer_id", "N/A")))
        hname = html.escape(str(off.get("hotel_name", "N/A")))
        site = html.escape(str(off.get("site", "N/A")))
        status = html.escape(str(off.get("status", "unverified")))
        recon = html.escape(str(off.get("reconciliation", "N/A")))
        room = html.escape(str(off.get("room_type") or "Standard Room"))
        meal = html.escape(str(off.get("meal_plan") or "Room only"))
        cancellation = html.escape(str(off.get("cancellation_policy") or "Non-refundable"))
        price_list = off.get("price_shown_on_listing")
        price_final = off.get("price_final_payable")
        leak_pct = off.get("fee_leak_pct")
        currency = html.escape(str(off.get("currency", "INR")))
        started = html.escape(str(off.get("started_at", "N/A")))
        finished = html.escape(str(off.get("finished_at", "N/A")))

        price_list_str = f"{currency} {price_list:,.2f}" if price_list is not None else "N/A"
        price_final_str = f"{currency} {price_final:,.2f}" if price_final is not None else "N/A"
        leak_str = f"+{leak_pct:.1f}%" if leak_pct is not None else "N/A"

        # Fee lines
        fee_rows = []
        for fl in off.get("fee_lines", []):
            fl_lbl = html.escape(str(fl.get("label", "Fee")))
            fl_amt = fl.get("amount", 0.0)
            fl_kind = html.escape(str(fl.get("fee_kind", "other")))
            fee_rows.append(
                f"<tr><td>{fl_lbl}</td><td><span class='badge badge-secondary'>{fl_kind}</span></td>"
                f"<td class='text-right'>{currency} {fl_amt:,.2f}</td></tr>"
            )
        fee_tbody = "".join(fee_rows) if fee_rows else "<tr><td colspan='3'>No individual fee lines observed.</td></tr>"

        # Price trail
        trail_rows = []
        for tp in off.get("price_trail", []):
            step_name = html.escape(str(tp.get("step", "")).replace("_", " ").title())
            tp_amt = tp.get("amount", 0.0)
            tp_curr = html.escape(str(tp.get("currency", currency)))
            trail_rows.append(f"<tr><td>{step_name}</td><td class='text-right'>{tp_curr} {tp_amt:,.2f}</td></tr>")
        trail_tbody = "".join(trail_rows) if trail_rows else "<tr><td colspan='2'>No trail points recorded.</td></tr>"

        # Pressure messages
        urgency = off.get("urgency_or_scarcity_messages", [])
        addons = off.get("preselected_addons", [])
        urgency_html = (
            "".join(f"<li>{html.escape(str(m))}</li>" for m in urgency)
            if urgency
            else "<em>None detected on this run.</em>"
        )
        addons_html = (
            "".join(f"<li>{html.escape(str(a))}</li>" for a in addons)
            if addons
            else "<em>None observed.</em>"
        )

        # Evidence links
        evidence_items = off.get("evidence", [])
        evidence_links = []
        for ev in evidence_items:
            ev_type = html.escape(str(ev.get("type", "screenshot")))
            ev_url = html.escape(str(ev.get("url", "#")))
            ev_step = html.escape(str(ev.get("step", "")))
            evidence_links.append(f"<li><strong>{ev_step}</strong>: <a href='{ev_url}'>{ev_type} ({ev_url})</a></li>")
        ev_html = "".join(evidence_links) if evidence_links else "<em>No standalone artifacts captured.</em>"

        status_class = "status-verified" if status == "verified" else "status-other"

        offers_html.append(f"""
        <div class="offer-card">
            <div class="offer-header">
                <div>
                    <h3 style="margin: 0 0 4px 0;">{hname}</h3>
                    <span class="badge badge-platform">{site}</span>
                    <span class="badge {status_class}">{status.upper()}</span>
                    <span class="badge badge-secondary">Reconciliation: {recon}</span>
                </div>
                <div class="text-right">
                    <div style="font-size: 13px; color: #64748b;">Observed Payable Price</div>
                    <div style="font-size: 22px; font-weight: 700; color: #0f172a;">{price_final_str}</div>
                    <div style="font-size: 12px; color: #e11d48; font-weight: 600;">{leak_str} vs initial listing ({price_list_str})</div>
                </div>
            </div>

            <div class="grid grid-2" style="margin-top: 16px;">
                <div>
                    <p style="margin: 4px 0;"><strong>Room Type:</strong> {room}</p>
                    <p style="margin: 4px 0;"><strong>Meal Plan:</strong> {meal}</p>
                    <p style="margin: 4px 0;"><strong>Cancellation:</strong> {cancellation}</p>
                </div>
                <div>
                    <p style="margin: 4px 0;"><strong>Offer ID:</strong> <code>{oid}</code></p>
                    <p style="margin: 4px 0;"><strong>Timeline:</strong> {started} &rarr; {finished}</p>
                    <p style="margin: 4px 0; color: #475569;"><em>Observed on this run under guest conditions.</em></p>
                </div>
            </div>

            <div class="grid grid-2" style="margin-top: 16px;">
                <div>
                    <h4 style="margin: 0 0 8px 0;">Price Trail Checkpoints</h4>
                    <table>
                        <thead><tr><th>Step</th><th class="text-right">Amount</th></tr></thead>
                        <tbody>{trail_tbody}</tbody>
                    </table>
                </div>
                <div>
                    <h4 style="margin: 0 0 8px 0;">Observed Fee Lines Breakdown</h4>
                    <table>
                        <thead><tr><th>Line Item</th><th>Kind</th><th class="text-right">Amount</th></tr></thead>
                        <tbody>{fee_tbody}</tbody>
                    </table>
                </div>
            </div>

            <div class="grid grid-2" style="margin-top: 16px;">
                <div class="subcard">
                    <h4 style="margin: 0 0 6px 0;">Urgency & Scarcity Signals</h4>
                    <ul style="margin: 0; padding-left: 20px;">{urgency_html}</ul>
                </div>
                <div class="subcard">
                    <h4 style="margin: 0 0 6px 0;">Pre-Selected Add-ons</h4>
                    <ul style="margin: 0; padding-left: 20px;">{addons_html}</ul>
                </div>
            </div>

            <div style="margin-top: 12px;">
                <h4 style="margin: 0 0 6px 0;">Captured Evidence Links</h4>
                <ul style="margin: 0; padding-left: 20px;">{ev_html}</ul>
            </div>
        </div>
        """)

    all_offers_html = "".join(offers_html) if offers_html else "<p>No offers available for this search.</p>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TinyTravel Evidence Report - Search {sid}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm 15mm 15mm 15mm;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #1e293b;
            background-color: #ffffff;
            line-height: 1.5;
            margin: 0;
            padding: 24px;
        }}
        .report-header {{
            border-bottom: 2px solid #0f172a;
            padding-bottom: 16px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .title {{
            font-size: 26px;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }}
        .subtitle {{
            font-size: 14px;
            color: #64748b;
            margin-top: 4px;
        }}
        .callout-safety {{
            background-color: #eff6ff;
            border-left: 4px solid #3b82f6;
            padding: 12px 16px;
            border-radius: 4px;
            margin-bottom: 24px;
            font-size: 13px;
            color: #1e3a8a;
        }}
        .grid {{
            display: grid;
            gap: 16px;
        }}
        .grid-2 {{
            grid-template-columns: 1fr 1fr;
        }}
        .grid-4 {{
            grid-template-columns: repeat(4, 1fr);
        }}
        .stat-card {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 16px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 22px;
            font-weight: 700;
            color: #0f172a;
        }}
        .stat-label {{
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
            margin-top: 2px;
        }}
        .offer-card {{
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 18px;
            margin-bottom: 24px;
            background: #ffffff;
            page-break-inside: avoid;
        }}
        .offer-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 12px;
        }}
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            margin-right: 4px;
        }}
        .badge-platform {{
            background-color: #e0f2fe;
            color: #0369a1;
        }}
        .status-verified {{
            background-color: #dcfce7;
            color: #15803d;
        }}
        .status-other {{
            background-color: #fee2e2;
            color: #b91c1c;
        }}
        .badge-secondary {{
            background-color: #f1f5f9;
            color: #475569;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{
            padding: 6px 10px;
            border-bottom: 1px solid #e2e8f0;
            text-align: left;
        }}
        th {{
            background-color: #f8fafc;
            font-weight: 600;
            color: #475569;
        }}
        .text-right {{
            text-align: right;
        }}
        .subcard {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 12px;
        }}
        @media print {{
            body {{
                padding: 0;
            }}
            .offer-card {{
                box-shadow: none;
                border: 1px solid #94a3b8;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <div>
            <h1 class="title">TinyTravel Evidence Report</h1>
            <div class="subtitle">Search ID: <strong>{sid}</strong> &bull; Generated: {now_str}</div>
        </div>
        <div class="text-right">
            <span class="badge badge-platform" style="font-size: 13px; padding: 4px 10px;">Observed On This Run</span>
        </div>
    </div>

    <div class="callout-safety">
        <strong>Safety & Ethics Invariant:</strong> {SAFETY_STATEMENT}
    </div>

    <section style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 12px 0;">Request & Parameters</h3>
        <div class="grid grid-4">
            <div class="stat-card">
                <div class="stat-value">{destination}</div>
                <div class="stat-label">Destination</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{check_in} &rarr; {check_out}</div>
                <div class="stat-label">Dates (Stay)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{guests} Guests, {rooms} Room</div>
                <div class="stat-label">Occupancy</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{deal_mode}</div>
                <div class="stat-label">Ranking Mode</div>
            </div>
        </div>
    </section>

    <section style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 12px 0;">Investigation Summary</h3>
        <div class="grid grid-4">
            <div class="stat-card">
                <div class="stat-value">{listings_found}</div>
                <div class="stat-label">Listings Found</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{unique_hotels}</div>
                <div class="stat-label">Unique Properties</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #15803d;">{verified_count}</div>
                <div class="stat-label">Verified (At Payment)</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #e11d48;">{avg_leak_str}</div>
                <div class="stat-label">Avg Fee Leak %</div>
            </div>
        </div>
    </section>

    <section style="margin-bottom: 24px;">
        <h3 style="margin: 0 0 8px 0;">Algorithmic Verdicts</h3>
        <div class="subcard">
            <p style="margin: 4px 0;"><strong>Best Value Offer:</strong> {best_hl}</p>
            <p style="margin: 4px 0;"><strong>Cheapest Verified:</strong> {cheapest_hl}</p>
            <p style="margin: 4px 0;"><strong>Safest Pick (Free Cancellation):</strong> {safe_hl}</p>
        </div>
    </section>

    <section>
        <h3 style="margin: 0 0 16px 0;">Verified Offers & Observed Evidence</h3>
        {all_offers_html}
    </section>
</body>
</html>"""


def generate_fee_draft(offer: dict) -> dict:
    """Generate a polite, factual draft inquiry message about an observed fee."""
    platform = offer.get("site") or "Booking Platform"
    hotel_name = offer.get("hotel_name") or "the property"
    price_listing = offer.get("price_shown_on_listing")
    price_payable = offer.get("price_final_payable")
    leak_pct = offer.get("fee_leak_pct")
    currency = offer.get("currency") or "INR"
    timestamp = offer.get("finished_at") or offer.get("started_at") or "recent checkout"
    room_type = offer.get("room_type") or "Selected room"

    fee_lines_items = []
    for fl in offer.get("fee_lines", []):
        lbl = fl.get("label", "Fee")
        amt = fl.get("amount", 0.0)
        kind = fl.get("fee_kind", "other")
        fee_lines_items.append(f"  - {lbl} ({kind}): {currency} {amt:,.2f}")

    fee_breakdown_text = "\n".join(fee_lines_items) if fee_lines_items else "  - (No separate fee line breakdown provided on checkout page)"

    diff = (price_payable - price_listing) if (price_payable is not None and price_listing is not None) else None
    diff_str = f"{currency} {diff:,.2f}" if diff is not None else "N/A"
    leak_str = f"{leak_pct:.1f}%" if leak_pct is not None else "N/A"
    listing_str = f"{currency} {price_listing:,.2f}" if price_listing is not None else "N/A"
    payable_str = f"{currency} {price_payable:,.2f}" if price_payable is not None else "N/A"

    subject = f"Inquiry regarding fee breakdown for booking at {hotel_name}"
    message = (
        f"Dear {platform} Support Team,\n\n"
        f"I am writing to inquire about the pricing and fee breakdown observed during the checkout process for {hotel_name}.\n\n"
        f"Observed Details:\n"
        f"- Hotel: {hotel_name}\n"
        f"- Room Type: {room_type}\n"
        f"- Observation Timestamp: {timestamp}\n"
        f"- Initial Listing Price: {listing_str}\n"
        f"- Final Payable Price (Payment Page): {payable_str}\n"
        f"- Total Observed Difference: {diff_str} (observed increase: {leak_str})\n\n"
        f"Observed Fee Lines:\n"
        f"{fee_breakdown_text}\n\n"
        f"Could you please provide clarification on the calculation and components of these fee lines?\n\n"
        f"Thank you for your assistance.\n\n"
        f"Sincerely,\n"
        f"[Your Name]"
    )

    return {
        "offer_id": offer.get("offer_id", "unknown"),
        "platform": platform,
        "hotel_name": hotel_name,
        "subject": subject,
        "draft_message": message,
        "observed_leak_pct": leak_pct,
        "observed_price_initial": price_listing,
        "observed_price_final": price_payable,
        "currency": currency,
    }
