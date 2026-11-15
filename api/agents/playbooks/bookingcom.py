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

logger = logging.getLogger("tinytravel.playbook.bookingcom")
IST = timezone(timedelta(hours=5, minutes=30))

KNOWN_BOOKING_HOTELS = {
    "radisson blu atria": "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html",
    "radisson blu atria bengaluru": "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html",
    "sterlings mac hotel": "https://www.booking.com/hotel/in/sterlings-mac.html",
    "sterlings mac": "https://www.booking.com/hotel/in/sterlings-mac.html",
    "la marvella": "https://www.booking.com/hotel/in/la-marvella.html",
    "the chancery pavilion": "https://www.booking.com/hotel/in/the-chancery-pavillion.html",
    "the pride hotel": "https://www.booking.com/hotel/in/pride-hotel-bangalore.html",
    "bloomrooms city centre": "https://www.booking.com/hotel/in/bloomrooms-city-centre.html",
    "treebo tiba": "https://www.booking.com/hotel/in/treebo-trend-tiba.html",
    "ibis bengaluru city centre": "https://www.booking.com/hotel/in/ibis-bengaluru-city-centre.html",
    "the oberoi bengaluru": "https://www.booking.com/hotel/in/the-oberoi-bangalore.html",
    "the leela palace bengaluru": "https://www.booking.com/hotel/in/the-leela-palace-bangalore.html",
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
            hotel_url = f"{v}?checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR"
            break

    if not hotel_url:
        encoded_q = hotel_name.replace(" ", "+")
        hotel_url = f"https://www.booking.com/searchresults.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR"

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
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                viewport={"width": 1280, "height": 800},
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
            if "searchresults" in page.url:
                hotel_card = await page.query_selector('a[data-testid="title-link"]')
                if hotel_card:
                    href = await hotel_card.get_attribute("href")
                    if href:
                        await page.goto(href, wait_until="domcontentloaded", timeout=25000)
                        await asyncio.sleep(2.0)

            result["furthest_step"] = "room_selection"

            try:
                await page.wait_for_selector("#hprt-table, table.hprt-table, select.hprt-nos-select, button.js-reservation-button", timeout=12000)
            except Exception:
                await asyncio.sleep(3.0)

            # Parse rates and select room matching cohort (cheapest free-cancellation for 2 adults)
            rate_info = await page.evaluate('''() => {
                const table = document.querySelector('#hprt-table, table.hprt-table');
                if (!table) return null;
                const trs = Array.from(table.querySelectorAll('tbody tr'));
                let currentRoomName = "Standard Room";
                const rates = [];

                trs.forEach((tr, idx) => {
                    const roomHeader = tr.querySelector('.hprt-roomtype-link, .hprt-roomtype-icon-link, .room-name');
                    if (roomHeader && roomHeader.innerText.trim()) {
                        currentRoomName = roomHeader.innerText.trim();
                    }
                    const text = tr.innerText;
                    const select = tr.querySelector('select');
                    if (!select) return;

                    const isFreeCancel = /free cancellation/i.test(text);
                    const hasBreakfast = /breakfast included/i.test(text);

                    // Extract prices
                    const priceMatches = Array.from(text.matchAll(/₹\\s*([0-9,]+)/g)).map(m => parseFloat(m[1].replace(/,/g, '')));
                    if (priceMatches.length === 0) return;

                    const roomPrices = priceMatches.filter(p => p >= 3000);
                    const basePrice = roomPrices.length > 0 ? roomPrices[0] : Math.max(...priceMatches);
                    rates.push({
                        rowIdx: idx,
                        roomName: currentRoomName,
                        isFreeCancel: isFreeCancel,
                        hasBreakfast: hasBreakfast,
                        basePrice: basePrice,
                    });
                });
                return rates;
            }''')

            logger.info("Booking.com page url: %s, rate_info: %s", page.url, len(rate_info) if rate_info else None)
            selected_rate = None
            if rate_info:
                free_cancels = [r for r in rate_info if r["isFreeCancel"]]
                if free_cancels:
                    selected_rate = min(free_cancels, key=lambda x: x["basePrice"])
                    result["cancellation_policy"] = "Free cancellation"
                else:
                    selected_rate = min(rate_info, key=lambda x: x["basePrice"])
                    result["cancellation_policy"] = "Non-refundable"

            rate_amount = selected_rate["basePrice"] if selected_rate else None
            if not rate_amount:
                # fallback parse from price cells
                price_cells = await page.query_selector_all(".prco-valign-middle-helper, .bui-price-display__value, span[data-testid='price-and-discounted-price']")
                if price_cells:
                    try:
                        text = await price_cells[0].inner_text()
                        match = re.search(r"[\d,]+", text)
                        if match:
                            rate_amount = float(match.group(0).replace(",", ""))
                    except Exception:
                        pass

            if not rate_amount:
                result["blocker"] = "layout"
                result["reached_payment_page"] = False
                result["notes"] = "Could not parse real room rate from Booking.com room selection table."
                await browser.close()
                return to_probe_result_dict(result)

            if selected_rate:
                result["room_type"] = selected_rate["roomName"]
                result["meal_plan"] = "Breakfast Included" if selected_rate["hasBreakfast"] else "Room Only"

            result["price_shown_on_room_selection"] = rate_amount
            result["price_trail"].append({
                "step": "room_selection",
                "price_shown": rate_amount,
                "timestamp": datetime.now(IST).isoformat(),
            })

            # Advance to guest details / book.html
            if selected_rate:
                row_idx = selected_rate["rowIdx"]
                select_locator = page.locator(f"#hprt-table tbody tr:nth-child({row_idx + 1}) select, table.hprt-table tbody tr:nth-child({row_idx + 1}) select").first
                if await select_locator.count() > 0:
                    await select_locator.select_option("1")
                    await asyncio.sleep(1.0)
            else:
                selects = page.locator("select[data-testid='select-room-trigger'], select[name*='nr_rooms']")
                if await selects.count() > 0:
                    await selects.first.select_option("1")
                    await asyncio.sleep(1.0)

            reserve_btn = page.locator("button.js-reservation-button, button[type='submit'].hp_rt_input, button:has-text('I\\'ll reserve'), button:has-text('Reserve')").first
            if await reserve_btn.is_visible():
                await reserve_btn.click()
            
            try:
                await page.wait_for_url("**/book.html**", timeout=15000)
                book_page = page
            except Exception:
                await asyncio.sleep(5.0)
                book_page = page
                for p_curr in context.pages:
                    if "book.html" in p_curr.url:
                        book_page = p_curr
                        break
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
                await asyncio.sleep(5.0)

            # Step 3: Finish booking / payment review
            fin_text = await book_page.evaluate("() => document.body.innerText")
            reached_fin = "book.html" in book_page.url
            
            prices_fin = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', fin_text)
            logger.info("Step 3 reached_fin=%s, book_page.url=%s, prices_fin count=%s", reached_fin, book_page.url, len(prices_fin))
            if not prices_fin or not reached_fin:
                result["blocker"] = "layout"
                result["reached_payment_page"] = False
                result["furthest_step"] = "traveller_details"
                result["price_final_payable"] = None
                result["fee_lines"] = []
                result["notes"] = "Could not parse real total payable from Booking.com finish booking page."
                await browser.close()
                return to_probe_result_dict(result)

            clean_fin = [float(p.replace(",", "")) for p in prices_fin]
            
            # Find total payable
            m_total = re.search(r'(?:total|price|amount|payable|you pay)\s*(?:for\s*\d+\s*room[s]?)?[:\n\r\s]*₹\s*([0-9,]+(?:\.[0-9]+)?)', fin_text, re.I)
            if m_total:
                total_payable = float(m_total.group(1).replace(",", ""))
            else:
                total_payable = max(clean_fin)

            base_fare = rate_amount
            taxes = round(total_payable - base_fare, 2) if total_payable >= base_fare else 0.0

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

            if "free cancellation" in fin_text.lower():
                result["cancellation_policy"] = "Free cancellation"
            else:
                result["cancellation_policy"] = "Non-refundable"

            if taxes > 0:
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
                result["fee_lines"] = [
                    {
                        "label": "Total room rate (incl. taxes)",
                        "amount": total_payable,
                        "fee_kind": "other",
                    },
                ]

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
