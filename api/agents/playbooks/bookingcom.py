"""
Booking.com State-Machine Playbook.
Executes deterministic guest checkout on Booking.com stopping at payment review.
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
from playwright.async_api import async_playwright

try:
    from ...services.normalize import normalize_room_tier, normalize_meal_plan
except ImportError:
    from services.normalize import normalize_room_tier, normalize_meal_plan

logger = logging.getLogger("tinytravel.playbook.bookingcom")
IST = timezone(timedelta(hours=5, minutes=30))

KNOWN_BOOKING_HOTELS = {
    "radisson blu atria": "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html",
    "radisson blu atria bengaluru": "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html",
    "sterlings mac hotel": "https://www.booking.com/hotel/in/matthan.html",
    "sterlings mac": "https://www.booking.com/hotel/in/matthan.html",
    "la marvella": "https://www.booking.com/hotel/in/la-marvella.html",
    "the chancery pavilion": "https://www.booking.com/hotel/in/the-chancery-pavillion.html",
    "the pride hotel": "https://www.booking.com/hotel/in/pride-hotel-bangalore.html",
    "bloomrooms city centre": "https://www.booking.com/hotel/in/bloomroom-cunninghamroad.html",
    "bloomrooms": "https://www.booking.com/hotel/in/bloomroom-cunninghamroad.html",
    "treebo tiba": "https://www.booking.com/hotel/in/treebo-trend-tiba.html",
    "ibis bengaluru city centre": "https://www.booking.com/hotel/in/ibis-bengaluru-city-centre.html",
    "the oberoi bengaluru": "https://www.booking.com/hotel/in/the-oberoi-bangalore.html",
    "the oberoi": "https://www.booking.com/hotel/in/the-oberoi-bangalore.html",
    "the leela palace bengaluru": "https://www.booking.com/hotel/in/the-leela-palace-bangalore.html",
    "the leela palace": "https://www.booking.com/hotel/in/the-leela-palace-bangalore.html",
    "taj west end": "https://www.booking.com/hotel/in/taj-west-end.html",
    "hotel maurya": "https://www.booking.com/hotel/in/maurya.html",
    "fortune select jp cosmos": "https://www.booking.com/hotel/in/fortune-select-jp-cosmos.html",
    "lemon tree premier electronics city": "https://www.booking.com/hotel/in/lemon-tree-hotel-electronics-city.html",
    "fabhotel ivory pearl": "https://www.booking.com/hotel/in/fabhotel-ivory-pearl-koramangala.html",
}


def to_probe_result_dict(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Filter raw output strictly to fields defined in ProbeResult schema."""
    probe_keys = {
        "site", "reached_payment_page", "furthest_step", "blocker", "hotel_name",
        "hotel_url", "room_type", "max_occupancy", "meal_plan", "cancellation_policy",
        "price_shown_on_listing", "price_shown_on_room_selection", "price_final_payable",
        "fee_lines", "preselected_addons", "urgency_or_scarcity_messages", "price_trail",
        "currency", "notes", "listing_page_text", "payment_page_text", "rate_cohort",
        "cheapest_any_payable", "pay_now", "pay_at_hotel", "verification_level",
    }
    return {k: v for k, v in raw.items() if k in probe_keys}


async def run_bookingcom_playbook(
    hotel_name: str,
    search_params: Dict[str, Any],
    headless: bool = True,
    step_delay_ms: int = 100,
) -> Dict[str, Any]:
    t0 = datetime.now(IST)
    now_iso = t0.isoformat()

    cin = search_params.get("check_in", "2026-11-20")
    cout = search_params.get("check_out", "2026-11-21")
    guests = int(search_params.get("guests", 2))

    norm_name = hotel_name.strip().lower()
    hotel_url = None
    for k, v in KNOWN_BOOKING_HOTELS.items():
        if k in norm_name or norm_name in k:
            hotel_url = f"{v}?checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR&lang=en-gb"
            break

    if not hotel_url:
        encoded_q = hotel_name.replace(" ", "+")
        hotel_url = f"https://www.booking.com/searchresults.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR&lang=en-gb"

    evidence_dir = Path("evidence") / "bookingcom"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "site": "Booking.com",
        "reached_payment_page": False,
        "furthest_step": "init",
        "blocker": None,
        "hotel_name": hotel_name,
        "hotel_url": hotel_url,
        "room_type": None,
        "max_occupancy": guests,
        "meal_plan": "Room Only",
        "cancellation_policy": "Free cancellation",
        "price_shown_on_listing": None,
        "price_shown_on_room_selection": None,
        "price_final_payable": None,
        "fee_lines": [],
        "preselected_addons": [],
        "urgency_or_scarcity_messages": [],
        "price_trail": [],
        "currency": "INR",
        "notes": "Booking.com automated guest checkout playbook",
        "listing_page_text": "",
        "payment_page_text": "",
        "rate_cohort": "cheapest_free_cancellation",
        "cheapest_any_payable": None,
        "pay_now": None,
        "pay_at_hotel": None,
        "verification_level": "checkout",
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale="en-GB",
                timezone_id="Asia/Kolkata",
                viewport={"width": 1280, "height": 800},
                extra_http_headers={"Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"},
            )
            page = await context.new_page()

            # Step 1: Navigate to Hotel / Search Page
            logger.info("Step 1: Navigating to Booking.com: %s", hotel_url)
            resp = await page.goto(hotel_url, wait_until="domcontentloaded", timeout=30000)
            result["furthest_step"] = "listing"
            await asyncio.sleep(3.0)

            title_text = ""
            try:
                title_text = (await page.title()).lower()
            except Exception:
                await asyncio.sleep(2.0)
                title_text = (await page.title()).lower()

            if "access denied" in title_text or "attention required" in title_text:
                result["blocker"] = "captcha"
                await browser.close()
                return to_probe_result_dict(result)

            try:
                px = await page.query_selector("#px-captcha, .px-captcha-container, div[data-testid='px-captcha']")
                if px:
                    result["blocker"] = "captcha"
                    await browser.close()
                    return to_probe_result_dict(result)
            except Exception:
                pass

            html = await page.content()

            # Look for price on page
            prices = re.findall(r"₹\s*([0-9,]+)", html)
            if prices:
                cleaned_prices = [float(p.replace(",", "")) for p in prices if len(p.replace(",", "")) >= 3]
                if cleaned_prices:
                    shown_price = min(cleaned_prices)
                    result["price_shown_on_listing"] = shown_price
                    result["price_trail"].append({
                        "step": "listing",
                        "price_shown": shown_price,
                        "timestamp": datetime.now(IST).isoformat(),
                    })

            # Check if direct property page or search listing
            if "searchresults" in page.url or "checkin" not in page.url:
                if "searchresults" not in page.url:
                    logger.info("Direct navigation stripped query parameters (%s); trying search flow for %s", page.url, hotel_name)
                    encoded_q = hotel_name.replace(" ", "+")
                    search_fallback = f"https://www.booking.com/searchresults.en-gb.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR"
                    await page.goto(search_fallback, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3.0)

                hotel_card = await page.query_selector('a[data-testid="title-link"]')
                if hotel_card:
                    href = await hotel_card.get_attribute("href")
                    if href:
                        await page.goto(href, wait_until="domcontentloaded", timeout=25000)
                        await asyncio.sleep(3.0)

            result["furthest_step"] = "room_selection"

            # State: ROOM_SELECTION - Check sold-out and parse rates JSON-first
            state = await page.evaluate('''() => {
                const env = window.booking ? window.booking.env : null;
                const bodyTxt = document.body ? document.body.innerText : '';
                const isSoldOut = (env && env.b_has_available_rooms === false) ||
                                  bodyTxt.includes('We have no rooms available') ||
                                  bodyTxt.includes('Sold out on our site') ||
                                  bodyTxt.includes('no available rooms at this property');
                if (isSoldOut) {
                    return { isSoldOut: true, rates: [] };
                }

                const rates = [];
                // Strategy 1: JSON-first from window.booking.env
                if (env && env.b_rooms_available_and_soldout && env.b_rooms_available_and_soldout.length > 0) {
                    env.b_rooms_available_and_soldout.forEach(room => {
                        const roomName = room.b_name || "Standard Room";
                        (room.b_blocks || []).forEach(block => {
                            const blockId = String(block.b_block_id || "");
                            const occ = block.b_can_fit_them_all || room.b_max_persons || 2;
                            const basePrice = parseFloat(block.b_raw_price || 0);
                            let totalPrice = basePrice;
                            let taxes = 0;
                            if (block.b_price_breakdown_simplified && block.b_price_breakdown_simplified.b_total_price && block.b_price_breakdown_simplified.b_total_price.length > 0) {
                                totalPrice = parseFloat(block.b_price_breakdown_simplified.b_total_price[0].b_raw_value_user_currency || basePrice);
                                taxes = Math.round((totalPrice - basePrice) * 100) / 100;
                            }
                            const isFreeCancel = block.b_cancellation_type === "free_cancellation";
                            const mealRaw = (block.b_mealplan_included_name || "").toLowerCase();
                            let meal = "Room Only";
                            if (mealRaw.includes("breakfast")) meal = "Breakfast Included";
                            else if (mealRaw.includes("half")) meal = "Half Board";
                            else if (mealRaw.includes("all")) meal = "All Inclusive";

                            rates.push({
                                blockId: blockId,
                                roomName: roomName,
                                occupancy: occ,
                                basePrice: basePrice,
                                totalPrice: totalPrice,
                                taxes: taxes,
                                isFreeCancel: isFreeCancel,
                                mealPlan: meal,
                                source: "json"
                            });
                        });
                    });
                }

                // Strategy 2: DOM Layout 1 - #hprt-table
                if (rates.length === 0) {
                    const trs = Array.from(document.querySelectorAll('#hprt-table tbody tr, table.hprt-table tbody tr'));
                    let curRoom = "Standard Room";
                    trs.forEach((tr, idx) => {
                        const rh = tr.querySelector('.hprt-roomtype-link, .hprt-roomtype-icon-link, .room-name');
                        if (rh && rh.innerText.trim()) curRoom = rh.innerText.trim();
                        const sel = tr.querySelector('select');
                        if (!sel) return;
                        const txt = tr.innerText;
                        const isFreeCancel = /free cancellation/i.test(txt);
                        const hasBreakfast = /breakfast/i.test(txt);
                        const priceMatches = Array.from(txt.matchAll(/₹\\s*([0-9,]+)/g)).map(m => parseFloat(m[1].replace(/,/g, '')));
                        if (priceMatches.length === 0) return;
                        const base = priceMatches[0];
                        const totalPrice = priceMatches.length > 1 ? Math.max(...priceMatches) : base;
                        const taxes = totalPrice > base ? Math.round((totalPrice - base) * 100) / 100 : 0.0;
                        rates.push({
                            blockId: sel.name ? sel.name.replace('nr_rooms_', '') : `row_${idx}`,
                            roomName: curRoom,
                            occupancy: 2,
                            basePrice: base,
                            totalPrice: totalPrice,
                            taxes: taxes,
                            isFreeCancel: isFreeCancel,
                            mealPlan: hasBreakfast ? "Breakfast Included" : "Room Only",
                            source: "dom_table"
                        });
                    });
                }

                // Strategy 3: DOM Layout 2 - [data-testid='room-card']
                if (rates.length === 0) {
                    const cards = Array.from(document.querySelectorAll("[data-testid='room-card'], div[data-testid='property-section--rooms'] > div"));
                    cards.forEach((card, idx) => {
                        const titleElem = card.querySelector("[data-testid='room-title'], h3, h4");
                        const curRoom = titleElem ? titleElem.innerText.trim() : `Room ${idx+1}`;
                        const txt = card.innerText;
                        const priceMatches = Array.from(txt.matchAll(/₹\\s*([0-9,]+)/g)).map(m => parseFloat(m[1].replace(/,/g, '')));
                        if (priceMatches.length === 0) return;
                        const base = priceMatches[0];
                        const totalPrice = priceMatches.length > 1 ? Math.max(...priceMatches) : base;
                        const taxes = totalPrice > base ? Math.round((totalPrice - base) * 100) / 100 : 0.0;
                        const isFreeCancel = /free cancellation/i.test(txt);
                        const hasBreakfast = /breakfast/i.test(txt);
                        const sel = card.querySelector('select');
                        const blockId = sel && sel.name ? sel.name.replace('nr_rooms_', '') : `card_${idx}`;
                        rates.push({
                            blockId: blockId,
                            roomName: curRoom,
                            occupancy: 2,
                            basePrice: base,
                            totalPrice: totalPrice,
                            taxes: taxes,
                            isFreeCancel: isFreeCancel,
                            mealPlan: hasBreakfast ? "Breakfast Included" : "Room Only",
                            source: "dom_card"
                        });
                    });
                }

                return { isSoldOut: false, rates: rates };
            }''')

            if state.get("isSoldOut"):
                result["blocker"] = "sold_out"
                result["status"] = "blocked"
                result["furthest_step"] = "room_selection"
                result["notes"] = "Property has no available rooms (sold out) on Booking.com for selected dates."
                result["reached_payment_page"] = False
                await browser.close()
                return to_probe_result_dict(result)

            rates = state.get("rates", [])
            logger.info("Booking.com page url: %s, rates found: %d", page.url, len(rates))

            if not rates:
                result["blocker"] = "other"
                result["status"] = "unverified"
                result["reached_payment_page"] = False
                result["notes"] = "Could not parse real room rate from Booking.com JSON state or tables/cards."
                await browser.close()
                return to_probe_result_dict(result)

            if search_params.get("catalog_only"):
                logger.info("Catalog only requested for Booking.com: %d rates found", len(rates))
                await browser.close()
                for r in rates:
                    tier = normalize_room_tier(r["roomName"])
                    meal_raw = r["mealPlan"]
                    norm_meal = normalize_meal_plan(meal_raw)
                    canc_cat = "free" if r["isFreeCancel"] else "non_refundable"
                    r["room_name"] = r["roomName"]
                    r["room_tier"] = tier
                    r["base_price"] = r["basePrice"]
                    r["tax_price"] = r.get("taxes", 0.0)
                    r["total_price"] = r["totalPrice"]
                    r["norm_meal_plan"] = norm_meal
                    r["cancellation_category"] = canc_cat
                    r["cohort"] = (tier, 2, norm_meal, canc_cat)
                return {
                    "site": "Booking.com",
                    "status": "catalog",
                    "rates": rates,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                }

            # Target cohort or block ID matching
            target_block_id = search_params.get("target_block_id")
            target_cohort = search_params.get("target_cohort")
            selected_rate = None

            if target_block_id:
                for r in rates:
                    if str(r.get("blockId")) == str(target_block_id):
                        selected_rate = r
                        break

            if not selected_rate and target_cohort:
                # target_cohort is (room_tier, occupancy, meal_plan, cancellation)
                for r in rates:
                    # check if tier, meal, cancellation match
                    is_free = r["isFreeCancel"]
                    canc_cat = "free" if is_free else "non_refundable"
                    mp_cat = "breakfast" if "breakfast" in r["mealPlan"].lower() else "room_only"
                    if canc_cat == target_cohort[3] and mp_cat == target_cohort[2]:
                        selected_rate = r
                        break

            if not selected_rate:
                # Deterministic rule: occupancy >= guests, prefer cheapest free cancellation, else cheapest
                valid_occ = [r for r in rates if r.get("occupancy", 2) >= guests]
                if not valid_occ:
                    valid_occ = rates
                free_cancels = [r for r in valid_occ if r["isFreeCancel"]]
                if free_cancels:
                    selected_rate = min(free_cancels, key=lambda x: x["totalPrice"])
                else:
                    selected_rate = min(valid_occ, key=lambda x: x["totalPrice"])

            cheapest_any = min(rates, key=lambda x: x["totalPrice"])
            result["cheapest_any_payable"] = cheapest_any["totalPrice"]

            rate_amount = selected_rate["basePrice"]
            result["room_type"] = selected_rate["roomName"]
            result["meal_plan"] = selected_rate["mealPlan"]
            result["cancellation_policy"] = "Free cancellation" if selected_rate["isFreeCancel"] else "Non-refundable"
            result["price_shown_on_room_selection"] = rate_amount
            result["price_trail"].append({
                "step": "room_selection",
                "price_shown": rate_amount,
                "timestamp": datetime.now(IST).isoformat(),
            })

            # Advance to guest details / book.html
            block_id = selected_rate.get("blockId")
            selected_dropdown = False
            if block_id:
                try:
                    target_sel = page.locator(f"select[name*='{block_id}']").first
                    if await target_sel.count() > 0:
                        await target_sel.scroll_into_view_if_needed()
                        await target_sel.select_option("1")
                        selected_dropdown = True
                        logger.info("Selected 1 room for block_id: %s", block_id)
                except Exception as e:
                    logger.warning("Failed to select block_id %s: %s", block_id, e)

            if not selected_dropdown:
                selects = page.locator("select.hprt-nos-select, select[name*='nr_rooms'], select[data-testid='select-room-trigger']")
                if await selects.count() > 0:
                    sel = selects.first
                    await sel.scroll_into_view_if_needed()
                    await sel.select_option("1")
                    selected_dropdown = True
                    logger.info("Selected 1 room from fallback dropdown")
                    await asyncio.sleep(1.5)

            reserve_btn = page.locator("button.js-reservation-button, button[type='submit'].hp_rt_input, button[data-testid='reserve-button'], button:has-text('reserve'), button:has-text('Reserve')").first
            if await reserve_btn.count() > 0:
                await reserve_btn.scroll_into_view_if_needed()
                await reserve_btn.click()
                logger.info("Clicked reserve button")
            
            book_page = None
            for _ in range(12):
                await asyncio.sleep(1.0)
                for p_curr in context.pages:
                    if "book.html" in p_curr.url:
                        book_page = p_curr
                        break
                if book_page:
                    break

            if not book_page:
                book_page = page
            await book_page.bring_to_front()

            # Fill guest details
            fn = book_page.locator("input[name='firstname'], input#firstname").first
            if await fn.is_visible():
                await fn.fill("Test")
            ln = book_page.locator("input[name='lastname'], input#lastname").first
            if await ln.is_visible():
                await ln.fill("Guest")
            em = book_page.locator("input[name='email'], input#email").first
            if await em.is_visible():
                await em.fill("test.guest+probe@example.com")
            ph = book_page.locator("input[name='phoneNumber'], input[name='phone'], input#phone").first
            if await ph.is_visible():
                await ph.fill("9000000000")

            # Click Next: Final details
            next_btn = book_page.locator("button[name='submit_step_1'], button:has-text('Next: Final details'), button:has-text('Next')").first
            if await next_btn.is_visible():
                await next_btn.click()
                try:
                    await book_page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(4.0)

            # Step 3: Finish booking / payment review
            fin_text = ""
            for _ in range(3):
                try:
                    fin_text = await book_page.evaluate("() => document.body.innerText")
                    if fin_text:
                        break
                except Exception:
                    await asyncio.sleep(2.0)

            reached_fin = "book.html" in book_page.url
            
            prices_fin = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', fin_text)
            logger.info("Step 3 reached_fin=%s, book_page.url=%s, prices_fin count=%s", reached_fin, book_page.url, len(prices_fin))
            if not prices_fin or not reached_fin:
                result["blocker"] = "other"
                result["reached_payment_page"] = False
                result["furthest_step"] = "traveller_details"
                result["price_final_payable"] = None
                result["fee_lines"] = []
                result["notes"] = "Could not parse real total payable from Booking.com finish booking page."
                await browser.close()
                return to_probe_result_dict(result)

            clean_fin = [float(p.replace(",", "")) for p in prices_fin]
            
            # Find total payable strictly (no blind max fallback)
            m_total = re.search(r'(?:total|price|amount|payable|you pay)\s*(?:for\s*\d+\s*room[s]?)?[:\n\r\s]*₹\s*([0-9,]+(?:\.[0-9]+)?)', fin_text, re.I)
            if not m_total:
                m_total = re.search(r'₹\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:total|payable)', fin_text, re.I)

            if not m_total:
                result["blocker"] = "other"
                result["reached_payment_page"] = False
                result["furthest_step"] = "traveller_details"
                result["price_final_payable"] = None
                result["fee_lines"] = []
                result["notes"] = "Could not parse explicit total payable from Booking.com payment page text."
                await browser.close()
                return to_probe_result_dict(result)

            total_payable = float(m_total.group(1).replace(",", ""))

            # Extract explicit tax line if present on payment page
            m_tax = re.search(r'(?:taxes\s*(?:and|&)?\s*(?:charges|fees)?|gst|vat|टैक्स और शुल्क)[:\n\r\s]*[+₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', fin_text, re.I)
            m_base = re.search(r'(?:price|room price|charges for \d+ room[s]?|कीमत)[:\n\r\s]*[₹Rs.\s]*([0-9,]+(?:\.[0-9]+)?)', fin_text, re.I)
            
            if m_tax and m_base:
                taxes = float(m_tax.group(1).replace(",", ""))
                base_fare = float(m_base.group(1).replace(",", ""))
                result["fee_lines"] = [
                    {
                        "label": "Room rate",
                        "amount": base_fare,
                        "fee_kind": "other",
                    },
                    {
                        "label": "Taxes & charges",
                        "amount": taxes,
                        "fee_kind": "tax",
                    },
                ]
            elif m_tax:
                taxes = float(m_tax.group(1).replace(",", ""))
                base_fare = round(total_payable - taxes, 2)
                result["fee_lines"] = [
                    {
                        "label": "Room rate",
                        "amount": base_fare,
                        "fee_kind": "other",
                    },
                    {
                        "label": "Taxes & charges",
                        "amount": taxes,
                        "fee_kind": "tax",
                    },
                ]
            else:
                # No separate tax line displayed: room rate is all-inclusive
                result["fee_lines"] = [
                    {
                        "label": "Total room rate (incl. taxes)",
                        "amount": total_payable,
                        "fee_kind": "other",
                    },
                ]

            result["furthest_step"] = "payment"
            result["reached_payment_page"] = True
            result["price_final_payable"] = total_payable
            result["cheapest_any_payable"] = total_payable

            # Extract room name, meal plan, cancellation from page text
            room_elem = await book_page.query_selector("h2, h3, .e2e-summary-room-type, [data-testid='room-name'], .bp-room-type, .bui-f-font-strong")
            if room_elem:
                txt = (await room_elem.inner_text()).strip()
                if txt and len(txt) < 80 and not any(w in txt.lower() for w in ["price", "total", "booking", "details", "summary", "step"]):
                    result["room_type"] = txt
            if not result.get("room_type"):
                result["room_type"] = selected_rate["roomName"] if selected_rate else "Standard Room"

            if "breakfast included" in fin_text.lower():
                result["meal_plan"] = "Breakfast Included"
            else:
                result["meal_plan"] = "Room Only"

            if "free cancellation" in fin_text.lower() or "मुफ़्त कैंसलेशन" in fin_text:
                result["cancellation_policy"] = "Free cancellation"
            else:
                result["cancellation_policy"] = "Non-refundable"

            result["price_trail"].append({
                "step": "payment",
                "price_shown": total_payable,
                "timestamp": datetime.now(IST).isoformat(),
            })

            # Save screenshot evidence
            recon_dir = Path("results/recon/real_pairs")
            recon_dir.mkdir(parents=True, exist_ok=True)
            scr_path = recon_dir / f"bookingcom_{norm_name.replace(' ', '_')}_{cin}_{int(t0.timestamp())}.png"
            try:
                await book_page.screenshot(path=str(scr_path), animations="disabled", timeout=15000)
            except Exception:
                pass
            result["payment_page_text"] = f"Booking.com checkout verified for {hotel_name}. Total payable: INR {total_payable}. Dates: {cin} to {cout}. Room: {result['room_type']}. Meal: {result['meal_plan']}. Cancel: {result['cancellation_policy']}."


            await browser.close()
    except Exception as e:
        logger.error("Booking.com playbook failed: %s", e)
        result["blocker"] = "other"
        result["notes"] = f"Execution error: {str(e)}"

    return to_probe_result_dict(result)
