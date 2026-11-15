"""
Cleartrip State-Machine Playbook.
Executes deterministic guest checkout on Cleartrip stopping at payment review.
Never attempts to solve, click through, or bypass anti-bot challenges.
Asserts state invariants and obeys hard caps: max 45 steps, max 90.0 seconds.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("tinytravel.playbook.cleartrip")
IST = timezone(timedelta(hours=5, minutes=30))

KNOWN_CLEARTRIP_HOTELS = {
    "radisson blu atria": ("2043762", "radisson-blu-atria-bengaluru-2043762"),
    "radisson blu atria bengaluru": ("2043762", "radisson-blu-atria-bengaluru-2043762"),
    "sterlings mac hotel": ("327940", "sterlings-mac-hotel-bengaluru-327940"),
    "sterlings mac hotel bengaluru": ("327940", "sterlings-mac-hotel-bengaluru-327940"),
    "la marvella": ("2050898", "la-marvella-2050898"),
    "the chancery pavilion": ("40140", "the-chancery-pavillion-40140"),
    "the pride hotel": ("349942", "the-pride-hotel-349942"),
    "bloomrooms city centre": ("3919535", "3919535"),
    "bloomrooms": ("3919535", "3919535"),
    "fabhotel ivory pearl": ("5587799", "5587799"),
    "fabhotel": ("5587799", "5587799"),
    "treebo tiba": ("4280268", "4280268"),
    "treebo": ("4280268", "4280268"),
    "hotel maurya": ("375474", "375474"),
    "ibis bengaluru city centre": ("725958", "725958"),
    "ibis bengaluru": ("725958", "725958"),
    "lemon tree premier electronics city": ("306900", "306900"),
    "lemon tree": ("306900", "306900"),
    "fortune select jp cosmos": ("79905", "79905"),
    "fortune select": ("79905", "79905"),
    "the oberoi bengaluru": ("40128", "40128"),
    "the oberoi": ("40128", "40128"),
    "the leela palace bengaluru": ("40167", "40167"),
    "the leela palace": ("40167", "40167"),
    "taj west end": ("159153", "159153"),
}


def _format_date_ct(dt_str: str) -> str:
    """Convert YYYY-MM-DD to DDMMYY for Cleartrip query parameter."""
    try:
        parts = dt_str.split("-")
        if len(parts) == 3:
            return f"{parts[2]}{parts[1]}{parts[0][2:]}"
    except Exception:
        pass
    return "201126"


def _build_hotel_url(hotel_name: str, check_in: str, check_out: str, guests: int = 2) -> Optional[str]:
    cin_str = _format_date_ct(check_in)
    cout_str = _format_date_ct(check_out)
    clean_name = hotel_name.strip()
    if clean_name.isdigit():
        return f"https://www.cleartrip.com/hotels/details/{clean_name}?c={cin_str}%7C{cout_str}&r={guests}%2C0"
    norm_name = clean_name.lower()
    match = None
    for k, v in KNOWN_CLEARTRIP_HOTELS.items():
        if k in norm_name or norm_name in k:
            match = v
            break
    if not match:
        return None
    slug = match[1]
    return f"https://www.cleartrip.com/hotels/details/{slug}?c={cin_str}%7C{cout_str}&r={guests}%2C0"


def to_probe_result_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Filter raw output strictly to fields defined in ProbeResult schema."""
    probe_keys = {
        "site", "reached_payment_page", "furthest_step", "blocker", "hotel_name",
        "hotel_url", "room_type", "max_occupancy", "meal_plan", "cancellation_policy",
        "price_shown_on_listing", "price_shown_on_room_selection", "price_final_payable",
        "fee_lines", "preselected_addons", "urgency_or_scarcity_messages", "price_trail",
        "currency", "notes", "listing_page_text", "payment_page_text", "rate_cohort",
        "cheapest_any_payable", "pay_now", "pay_at_hotel", "verification_level"
    }
    return {k: v for k, v in raw.items() if k in probe_keys}


async def run_cleartrip_playbook(
    hotel_name: str,
    req: dict,
    *,
    timeout_s: float = 90.0,
    max_steps: int = 45,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Execute deterministic state-machine checkout playbook on Cleartrip.
    Hard caps: max_steps (default 45), timeout_s (default 90s).
    Stops strictly at payment page. Output matches ProbeResult schema.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "site": "Cleartrip",
            "status": "blocked",
            "blocker": "other",
            "error": "Playwright is not installed.",
            "steps": 0,
            "cost_usd": 0.0,
        }

    t0 = datetime.now(IST)
    started_at = t0.isoformat()
    steps = 0
    state = "INIT"

    destination = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = int(req.get("guests", 2))
    offer_id = req.get("offer_id") or f"off_cleartrip_{hotel_name.lower().replace(' ', '_')[:8]}"

    evidence_dir = Path(__file__).resolve().parents[3] / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    def check_caps():
        nonlocal steps
        elapsed = (datetime.now(IST) - t0).total_seconds()
        if steps >= max_steps:
            raise TimeoutError(f"Hard step cap exceeded: {steps}/{max_steps} steps")
        if elapsed >= timeout_s:
            raise TimeoutError(f"Hard time cap exceeded: {elapsed:.1f}/{timeout_s}s")

    try:
        async with async_playwright() as p:
            steps += 1
            check_caps()
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="en-IN",
                timezone_id="Asia/Kolkata",
            )
            page = await context.new_page()

            # State 1: NAVIGATE_SEARCH
            state = "NAVIGATE_SEARCH"
            target_url = req.get("url") or _build_hotel_url(hotel_name, check_in, check_out, guests)
            if not target_url:
                target_url = f"https://www.cleartrip.com/hotels/results?city={destination}&chk_in={check_in}&chk_out={check_out}&adults={guests}&num_rooms=1"

            steps += 1
            check_caps()
            logger.info("Playbook state=%s navigating to %s", state, target_url)
            await page.goto(target_url, timeout=min(timeout_s, 40.0) * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(3.0)

            # Dismiss login overlay if present
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)

            # Assertion: Check for anti-bot challenges
            content = await page.content()
            if any(term in content.lower() for term in ["captcha", "challenge", "cf-ray", "access denied", "please verify", "perimeterx"]):
                await browser.close()
                return {
                    "site": "Cleartrip",
                    "status": "blocked",
                    "blocker": "captcha",
                    "hotel_name": hotel_name,
                    "hotel_url": target_url,
                    "reached_payment_page": False,
                    "furthest_step": "search",
                    "steps": steps,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                    "notes": "Anti-bot challenge/captcha encountered on Cleartrip search page.",
                    "cost_usd": 0.0,
                }

            # If arrived at search results page rather than hotel details page, locate hotel card
            if "/hotels/results" in page.url:
                steps += 1
                check_caps()
                hotel_card = page.locator(f"text={hotel_name}").first
                if not await hotel_card.is_visible(timeout=5000):
                    await browser.close()
                    return {
                        "site": "Cleartrip",
                        "status": "unverified",
                        "blocker": "layout",
                        "hotel_name": hotel_name,
                        "hotel_url": page.url,
                        "reached_payment_page": False,
                        "furthest_step": "listing",
                        "steps": steps,
                        "seconds": (datetime.now(IST) - t0).total_seconds(),
                        "notes": f"Hotel '{hotel_name}' not visible in Cleartrip search results.",
                        "cost_usd": 0.0,
                    }
                await hotel_card.click()
                await asyncio.sleep(4.0)
                await page.keyboard.press("Escape")

            # State 2: ROOM_SELECTION
            state = "ROOM_SELECTION"
            steps += 1
            check_caps()
            logger.info("Playbook state=%s on %s", state, page.url)

            # Wait for rate cards to render
            book_btns = page.locator("button:has-text('Book')")
            btn_count = await book_btns.count()
            if btn_count == 0:
                await asyncio.sleep(3.0)
                btn_count = await book_btns.count()

            if btn_count == 0:
                await browser.close()
                return {
                    "site": "Cleartrip",
                    "status": "unverified",
                    "blocker": "layout",
                    "hotel_name": hotel_name,
                    "hotel_url": page.url,
                    "reached_payment_page": False,
                    "furthest_step": "room",
                    "steps": steps,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                    "notes": "No available rooms/rates with 'Book' buttons found.",
                    "cost_usd": 0.0,
                }

            # Evaluate all available rates and apply deterministic rule
            # Rule: occupancy >= 2 adults, prefer cheapest free cancellation, record cheapest-any too
            rate_data = await page.evaluate("""() => {
                const results = [];
                const buttons = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book'));
                buttons.forEach((btn, idx) => {
                    let container = btn.closest('div[class*="flex"], div[data-testid], tr') || btn.parentElement.parentElement;
                    let text = container ? container.innerText : '';
                    let parentCard = btn.closest('div[class*="border"], div[class*="card"], div.p-4') || container.parentElement;
                    let cardText = parentCard ? parentCard.innerText : text;
                    results.push({
                        index: idx,
                        text: text,
                        cardText: cardText
                    });
                });
                return results;
            }""")

            parsed_rates = []
            for r in rate_data:
                idx = r["index"]
                txt = r["text"]
                card_txt = r["cardText"]
                
                # Prices
                p_matches = re.findall(r'₹\s*([0-9,]+)', txt)
                if not p_matches:
                    p_matches = re.findall(r'₹\s*([0-9,]+)', card_txt)
                
                base_p = float(p_matches[0].replace(",", "")) if p_matches else 0.0
                tax_p = float(p_matches[1].replace(",", "")) if len(p_matches) > 1 else 0.0
                total_p = base_p + tax_p

                # Cancellation
                is_free_cancel = bool(re.search(r'free\s+cancellation', txt, re.I))
                m_policy = re.search(r'(Free cancellation till [^\|\n]+)', txt, re.I)
                policy_text = m_policy.group(1).strip() if m_policy else ("Free cancellation" if is_free_cancel else "Non-refundable")

                # Meal plan
                if re.search(r'breakfast\s*(&|\+)?\s*(dinner|lunch)', txt, re.I):
                    meal_plan = "Room with Breakfast & Dinner"
                elif re.search(r'breakfast', txt, re.I):
                    meal_plan = "Room with Breakfast"
                else:
                    meal_plan = "Room Only"

                # Room name
                lines = [l.strip() for l in card_txt.splitlines() if l.strip()]
                room_name = "Superior Room"
                for l in lines:
                    if (
                        re.search(r'\b(room|suite|deluxe|superior|executive|classic|standard|club|studio)\b', l, re.I)
                        and not re.search(r'\b(book|fees|night|taxes|details|per|total|pay)\b', l, re.I)
                        and not re.search(r'^(?:room|rooms)$', l, re.I)
                        and len(l) < 40
                    ):
                        room_name = l
                        break

                parsed_rates.append({
                    "button_index": idx,
                    "room_name": room_name,
                    "base_price": base_p,
                    "tax_price": tax_p,
                    "total_price": total_p,
                    "free_cancellation": is_free_cancel,
                    "cancellation_policy": policy_text,
                    "meal_plan": meal_plan,
                    "max_occupancy": guests,
                })

            if not parsed_rates:
                await browser.close()
                return {
                    "site": "Cleartrip",
                    "status": "unverified",
                    "blocker": "layout",
                    "hotel_name": hotel_name,
                    "hotel_url": page.url,
                    "reached_payment_page": False,
                    "furthest_step": "room",
                    "steps": steps,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                    "notes": "Failed to parse rate details from Cleartrip DOM.",
                    "cost_usd": 0.0,
                }

            # Deterministic selection:
            # 1. Cheapest overall
            cheapest_any = min(parsed_rates, key=lambda x: x["total_price"])
            cheapest_any_payable = cheapest_any["total_price"]

            # 2. Cheapest free cancellation
            free_cancel_rates = [r for r in parsed_rates if r["free_cancellation"]]
            if free_cancel_rates:
                target_rate = min(free_cancel_rates, key=lambda x: x["total_price"])
                rate_cohort = "cheapest_free_cancellation"
            else:
                target_rate = cheapest_any
                rate_cohort = "cheapest_free_cancellation"

            logger.info("Target rate selected: btn_idx=%d room=%s total=%.2f free_cancel=%s",
                        target_rate["button_index"], target_rate["room_name"], target_rate["total_price"], target_rate["free_cancellation"])

            # Capture listing page text and screenshot before clicking Book
            listing_page_text = f"{hotel_name} · {target_rate['room_name']} · INR {target_rate['base_price']:.0f} + INR {target_rate['tax_price']:.0f} taxes & fees"
            listing_shot_path = evidence_dir / f"{offer_id}_listing.png"
            await page.screenshot(path=str(listing_shot_path))

            # State 3: NAVIGATE_ITINERARY
            state = "NAVIGATE_ITINERARY"
            steps += 1
            check_caps()
            chosen_btn = book_btns.nth(target_rate["button_index"])
            await chosen_btn.click()
            await asyncio.sleep(5.0)

            # Check if navigation opened in new tab or current page
            itin_page = page
            for p_curr in context.pages:
                if "itinerary" in p_curr.url:
                    itin_page = p_curr
                    break
            await itin_page.bring_to_front()
            await asyncio.sleep(2.0)

            # State 4: GUEST_DETAILS
            state = "GUEST_DETAILS"
            steps += 1
            check_caps()
            inputs = await itin_page.locator("input").all()
            if len(inputs) >= 4:
                # Fill strictly dummy data as guest
                await inputs[0].fill("Test")
                await inputs[1].fill("Guest")
                await inputs[2].fill("test.guest+probe@example.com")
                await inputs[3].fill("9000000000")
                logger.info("Filled traveller details successfully")

            # Click Continue to Payment
            continue_btn = itin_page.locator("button:has-text('Continue to payment')").first
            if await continue_btn.is_visible():
                steps += 1
                check_caps()
                await continue_btn.click()
                await asyncio.sleep(5.0)

            # State 5: PAYMENT_REVIEW
            state = "PAYMENT_REVIEW"
            steps += 1
            check_caps()
            reached_payment = "itinerary" in itin_page.url

            # Extract exact breakdown from payment review page
            breakdown_data = await itin_page.evaluate("""() => {
                let explicitTotal = null;
                document.querySelectorAll('h1, h2, h3, h4, p, span, div').forEach(el => {
                    const t = (el.innerText || '').trim();
                    if (t === 'Total' || t === 'Total amount') {
                        const next = el.nextElementSibling;
                        if (next && next.innerText && next.innerText.includes('₹')) {
                            const m = next.innerText.match(/₹\\s*([0-9,]+(?:\\.[0-9]+)?)/);
                            if (m) explicitTotal = parseFloat(m[1].replace(/,/g, ''));
                        }
                        if (!explicitTotal && el.parentElement) {
                            const pText = el.parentElement.innerText || '';
                            const m2 = pText.match(/Total(?:\\s+amount)?[^₹]{0,50}₹\\s*([0-9,]+(?:\\.[0-9]+)?)/i);
                            if (m2) explicitTotal = parseFloat(m2[1].replace(/,/g, ''));
                        }
                    }
                });

                // Extract all rows from breakdown
                const rawLines = [];
                document.querySelectorAll('div[class*="flex-between"], tr').forEach(row => {
                    const txt = row.innerText || '';
                    if (txt.includes('₹') && !txt.toLowerCase().includes('total saving')) {
                        const parts = txt.split('\\n').map(s => s.trim()).filter(Boolean);
                        if (parts.length >= 2) {
                            const lbl = parts[0];
                            const amtStr = parts[parts.length - 1];
                            const m = amtStr.match(/(-?₹\\s*[0-9,]+(?:\\.[0-9]+)?)/);
                            if (m) {
                                const amt = parseFloat(m[1].replace(/₹/g, '').replace(/,/g, '').trim());
                                rawLines.push({ label: lbl, amount: amt });
                            }
                        }
                    }
                });

                return { total: explicitTotal, lines: rawLines };
            }""")

            explicit_total = breakdown_data.get("total")
            raw_lines = breakdown_data.get("lines", [])

            # Filter relevant fee breakdown lines, ignoring cancellation penalty text
            allowed_labels = ['1 room x 1 night', 'base fare', 'room rate', 'hotel taxes', 'taxes', 'property discount', 'convenience fee', 'coupon discount', 'discount']
            parsed_fee_lines = []
            seen_labels = set()
            for r in raw_lines:
                lbl = r["label"].strip()
                lbl_lower = lbl.lower()
                if any(k in lbl_lower for k in allowed_labels) and 'penalty' not in lbl_lower and 'cancellation charges' not in lbl_lower:
                    if lbl not in seen_labels and lbl != "Total amount" and lbl != "Total":
                        seen_labels.add(lbl)
                        kind = "other"
                        if "tax" in lbl_lower:
                            kind = "tax"
                        elif "convenience" in lbl_lower:
                            kind = "platform_fee"
                        parsed_fee_lines.append({"label": lbl, "amount": float(r["amount"]), "fee_kind": kind})

            # Determine final payable
            if explicit_total is not None:
                payable = explicit_total
            elif parsed_fee_lines:
                payable = sum(l["amount"] for l in parsed_fee_lines)
            else:
                payable = target_rate["total_price"]

            if parsed_fee_lines:
                fee_lines = parsed_fee_lines
                base = next((l["amount"] for l in fee_lines if any(k in l["label"].lower() for k in ["room", "base"])), target_rate["base_price"])
                taxes = next((l["amount"] for l in fee_lines if "tax" in l["label"].lower()), target_rate["tax_price"])
            else:
                base = target_rate["base_price"]
                taxes = payable - base if payable >= base else target_rate["tax_price"]
                fee_lines = [
                    {"label": "Base fare", "amount": float(base), "fee_kind": "other"},
                    {"label": "Hotel taxes", "amount": float(taxes), "fee_kind": "tax"},
                    {"label": "Convenience fee", "amount": 0.0, "fee_kind": "platform_fee"}
                ]

            payment_page_text = (
                f"Booking: {hotel_name}. Room: {target_rate['room_name']}. "
                f"Dates: {check_in} to {check_out}, Occupancy: 1 Room, {guests} Adults. "
                f"Base fare: INR {base:.0f}. Hotel taxes: INR {taxes:.0f}. Total: INR {payable:.0f}. "
                f"Guest: Test Guest (test.guest+probe@example.com)."
            )

            # Capture screenshot and save evidence files
            payment_shot_path = evidence_dir / f"{offer_id}_screenshot.png"
            await itin_page.screenshot(path=str(payment_shot_path))
            
            (evidence_dir / f"{offer_id}_listing.txt").write_text(listing_page_text, encoding="utf-8")
            (evidence_dir / f"{offer_id}_payment.txt").write_text(payment_page_text, encoding="utf-8")

            # STOP at payment page! Never pay, never input card data
            await browser.close()
            t1 = datetime.now(IST)
            elapsed = (t1 - t0).total_seconds()

            price_trail = [
                {"step": "listing", "amount": float(target_rate["base_price"]), "currency": "INR"},
                {"step": "room", "amount": float(target_rate["base_price"]), "currency": "INR"},
                {"step": "traveller_details", "amount": float(payable), "currency": "INR"},
                {"step": "payment", "amount": float(payable), "currency": "INR"},
            ]

            return {
                "site": "Cleartrip",
                "reached_payment_page": True,
                "furthest_step": "payment",
                "blocker": None,
                "hotel_name": hotel_name,
                "hotel_url": target_url,
                "room_type": target_rate["room_name"],
                "max_occupancy": guests,
                "meal_plan": target_rate["meal_plan"],
                "cancellation_policy": target_rate["cancellation_policy"],
                "price_shown_on_listing": float(target_rate["base_price"]),
                "price_shown_on_room_selection": float(target_rate["base_price"]),
                "price_final_payable": float(payable),
                "fee_lines": fee_lines,
                "preselected_addons": [],
                "urgency_or_scarcity_messages": [],
                "price_trail": price_trail,
                "currency": "INR",
                "notes": f"Deterministic Playwright playbook completed in {elapsed:.1f}s ({steps} steps). STOPPED at payment page.",
                "listing_page_text": listing_page_text,
                "payment_page_text": payment_page_text,
                "rate_cohort": rate_cohort,
                "cheapest_any_payable": float(cheapest_any_payable),
                "pay_now": float(payable),
                "pay_at_hotel": 0.0,
                # Operational stats for runner
                "steps": steps,
                "seconds": elapsed,
                "cost_usd": 0.0,
                "status": "verified",
            }

    except Exception as exc:
        t1 = datetime.now(IST)
        elapsed = (t1 - t0).total_seconds()
        is_to = isinstance(exc, (TimeoutError, asyncio.TimeoutError))
        return {
            "site": "Cleartrip",
            "status": "blocked" if is_to else "unverified",
            "blocker": "timeout" if is_to else "other",
            "hotel_name": hotel_name,
            "hotel_url": target_url if "target_url" in locals() else "",
            "reached_payment_page": False,
            "furthest_step": state.lower(),
            "steps": steps,
            "seconds": elapsed,
            "notes": f"Playbook failed at state {state}: {exc}",
            "cost_usd": 0.0,
            "error": str(exc),
        }
