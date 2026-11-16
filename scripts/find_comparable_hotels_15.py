import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import sys
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from api.agents.playbooks.cleartrip import KNOWN_CLEARTRIP_HOTELS, _build_hotel_url
from api.agents.playbooks.bookingcom import KNOWN_BOOKING_HOTELS
from api.services.normalize import normalize_room_tier, normalize_meal_plan

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("find_comparable_15")
IST = timezone(timedelta(hours=5, minutes=30))

HOTELS_15 = [
    "bloomrooms city centre",
    "sterlings mac hotel",
    "the oberoi bengaluru",
    "radisson blu atria bengaluru",
    "la marvella",
    "the chancery pavilion",
    "the pride hotel",
    "hotel maurya",
    "ibis bengaluru city centre",
    "lemon tree premier electronics city",
    "fortune select jp cosmos",
    "the leela palace bengaluru",
    "taj west end",
    "treebo tiba",
    "fabhotel ivory pearl",
]

async def extract_cleartrip_catalog(hotel_name: str, cin: str, cout: str, guests: int = 2) -> List[Dict[str, Any]]:
    url = _build_hotel_url(hotel_name, cin, cout, guests)
    if not url:
        return []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4.0)
            await page.keyboard.press("Escape")

            # Extract rates
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

            rates = []
            for r in rate_data:
                txt = r["text"]
                card_txt = r["cardText"]
                p_matches = re.findall(r'₹\s*([0-9,]+)', txt) or re.findall(r'₹\s*([0-9,]+)', card_txt)
                base_p = float(p_matches[0].replace(",", "")) if p_matches else 0.0
                tax_p = float(p_matches[1].replace(",", "")) if len(p_matches) > 1 else 0.0
                total_p = base_p + tax_p

                is_free_cancel = bool(re.search(r'free\s+cancellation', txt, re.I))
                m_policy = re.search(r'(Free cancellation till [^\|\n]+)', txt, re.I)
                policy_text = m_policy.group(1).strip() if m_policy else ("Free cancellation" if is_free_cancel else "Non-refundable")

                if re.search(r'breakfast\s*(&|\+)?\s*(dinner|lunch)', txt, re.I):
                    meal_plan = "Room with Breakfast & Dinner"
                elif re.search(r'breakfast', txt, re.I):
                    meal_plan = "Room with Breakfast"
                else:
                    meal_plan = "Room Only"

                lines = [l.strip() for l in card_txt.splitlines() if l.strip()]
                room_name = "Standard Room"
                for l in lines:
                    if (
                        re.search(r'\b(room|suite|deluxe|superior|executive|classic|standard|club|studio|villa)\b', l, re.I)
                        and not re.search(r'\b(book|fees|night|taxes|details|per|total|pay|room only|breakfast|refundable|cancellation)\b', l, re.I)
                        and not re.search(r'^(?:room|rooms)$', l, re.I)
                        and len(l) < 50
                    ):
                        room_name = l
                        break

                tier = normalize_room_tier(room_name)
                meal_norm = normalize_meal_plan(meal_plan)
                canc_norm = "free" if is_free_cancel else "non_refundable"

                rates.append({
                    "source": "Cleartrip",
                    "hotel_name": hotel_name,
                    "room_name": room_name,
                    "normalized_tier": tier,
                    "occupancy": guests,
                    "meal_plan": meal_plan,
                    "normalized_meal": meal_norm,
                    "cancellation_policy": policy_text,
                    "normalized_cancellation": canc_norm,
                    "base_price": base_p,
                    "total_price": total_p,
                    "button_index": r["index"]
                })
            await browser.close()
            return rates
        except Exception as e:
            logger.warning("Cleartrip catalog extraction error for %s: %s", hotel_name, e)
            await browser.close()
            return []

async def extract_bookingcom_catalog(hotel_name: str, cin: str, cout: str, guests: int = 2) -> List[Dict[str, Any]]:
    norm_name = hotel_name.strip().lower()
    hotel_url = None
    for k, v in KNOWN_BOOKING_HOTELS.items():
        if k in norm_name or norm_name in k:
            hotel_url = f"{v}?checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR&lang=en-gb"
            break
    if not hotel_url:
        encoded_q = hotel_name.replace(" ", "+")
        hotel_url = f"https://www.booking.com/searchresults.en-gb.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 800},
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"}
        )
        page = await ctx.new_page()
        try:
            await page.goto(hotel_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4.0)

            # If parameter stripped or search page, search and click card
            if "searchresults" in page.url or "checkin" not in page.url:
                if "searchresults" not in page.url:
                    encoded_q = hotel_name.replace(" ", "+")
                    search_url = f"https://www.booking.com/searchresults.en-gb.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults={guests}&no_rooms=1&selected_currency=INR"
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(3.0)
                card = await page.query_selector('a[data-testid="title-link"]')
                if card:
                    href = await card.get_attribute("href")
                    if href:
                        await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(3.0)

            # Parse state
            state = await page.evaluate('''() => {
                const env = window.booking ? window.booking.env : null;
                const rates = [];
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
                                mealPlan: meal
                            });
                        });
                    });
                }
                return rates;
            }''')

            rates = []
            for r in state:
                tier = normalize_room_tier(r["roomName"])
                meal_norm = normalize_meal_plan(r["mealPlan"])
                canc_norm = "free" if r["isFreeCancel"] else "non_refundable"
                rates.append({
                    "source": "Booking.com",
                    "hotel_name": hotel_name,
                    "room_name": r["roomName"],
                    "normalized_tier": tier,
                    "occupancy": r["occupancy"],
                    "meal_plan": r["mealPlan"],
                    "normalized_meal": meal_norm,
                    "cancellation_policy": "Free cancellation" if r["isFreeCancel"] else "Non-refundable",
                    "normalized_cancellation": canc_norm,
                    "base_price": r["basePrice"],
                    "total_price": r["totalPrice"],
                    "block_id": r["blockId"]
                })
            await browser.close()
            return rates
        except Exception as e:
            logger.warning("Booking.com catalog extraction error for %s: %s", hotel_name, e)
            await browser.close()
            return []

def intersect_catalogs(ct_rates: List[Dict], bk_rates: List[Dict]) -> List[Dict[str, Any]]:
    matches = []
    for ct in ct_rates:
        if ct["occupancy"] < 2:
            continue
        for bk in bk_rates:
            if bk["occupancy"] < 2:
                continue
            # Match 4 dimensions: tier, occupancy>=2, meal plan, cancellation
            if (
                ct["normalized_tier"] == bk["normalized_tier"]
                and ct["normalized_meal"] == bk["normalized_meal"]
                and ct["normalized_cancellation"] == bk["normalized_cancellation"]
            ):
                matches.append({
                    "normalized_cohort": f"{ct['normalized_tier']}_occ2_{ct['normalized_meal']}_{ct['normalized_cancellation']}",
                    "tier": ct["normalized_tier"],
                    "meal": ct["normalized_meal"],
                    "cancellation": ct["normalized_cancellation"],
                    "ct_room_name": ct["room_name"],
                    "ct_base": ct["base_price"],
                    "ct_total": ct["total_price"],
                    "ct_button_index": ct["button_index"],
                    "bk_room_name": bk["room_name"],
                    "bk_base": bk["base_price"],
                    "bk_total": bk["total_price"],
                    "bk_block_id": bk["block_id"],
                })
    return matches

async def main():
    cin = "2026-11-20"
    cout = "2026-11-21"
    summary = []

    for idx, hotel in enumerate(HOTELS_15, 1):
        logger.info("[%d/15] Running Pass 1 (Catalog) for '%s'...", idx, hotel)
        ct_rates = await extract_cleartrip_catalog(hotel, cin, cout)
        bk_rates = await extract_bookingcom_catalog(hotel, cin, cout)

        logger.info("   -> Cleartrip rates: %d, Booking.com rates: %d", len(ct_rates), len(bk_rates))
        
        # Pass 2: Intersection
        matches = intersect_catalogs(ct_rates, bk_rates)
        logger.info("   -> Cohort intersection matches: %d", len(matches))

        summary.append({
            "hotel_name": hotel,
            "cleartrip_rates_count": len(ct_rates),
            "bookingcom_rates_count": len(bk_rates),
            "has_intersection": len(matches) > 0,
            "intersection_count": len(matches),
            "matched_cohorts": matches[:3], # top matches
            "ct_sample_rooms": list(set(r["room_name"] for r in ct_rates))[:3],
            "bk_sample_rooms": list(set(r["room_name"] for r in bk_rates))[:3],
        })
        await asyncio.sleep(1.0)

    out_file = Path("results/pass1_pass2_15hotels.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Completed Pass 1 & Pass 2 for 15 hotels! Results saved to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
