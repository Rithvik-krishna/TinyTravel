import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import json
import logging
from playwright.async_api import async_playwright
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_booking_6hotels")
IST = timezone(timedelta(hours=5, minutes=30))

HOTELS_6 = [
    ("Radisson Blu Atria Bengaluru", "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html"),
    ("Sterlings Mac Hotel", "https://www.booking.com/hotel/in/matthan.html"),
    ("La Marvella", "https://www.booking.com/hotel/in/la-marvella.html"),
    ("Bloomrooms City Centre", "https://www.booking.com/hotel/in/bloomroom-cunninghamroad.html"),
    ("Treebo Tiba", "https://www.booking.com/hotel/in/treebo-trend-tiba.html"),
    ("The Oberoi Bengaluru", "https://www.booking.com/hotel/in/the-oberoi-bangalore.html"),
]

async def test_hotel(name, url, cin="2026-11-20", cout="2026-11-21"):
    full_url = f"{url}?checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1&selected_currency=INR"
    t0 = datetime.now(IST)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        logger.info("Testing %s on %s", name, full_url)
        try:
            await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4.0)

            title = (await page.title()).lower()
            if "access denied" in title or "attention required" in title:
                dur = (datetime.now(IST) - t0).total_seconds()
                await browser.close()
                return {"hotel": name, "status": "blocked", "blocker": "captcha", "rates": 0, "seconds": round(dur, 2)}

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

                // Fallback to DOM table
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
                        const base = priceMatches.find(p => p >= 2000) || priceMatches[0];
                        rates.push({
                            blockId: sel.name ? sel.name.replace('nr_rooms_', '') : `row_${idx}`,
                            roomName: curRoom,
                            occupancy: 2,
                            basePrice: base,
                            totalPrice: base * 1.18,
                            taxes: base * 0.18,
                            isFreeCancel: isFreeCancel,
                            mealPlan: hasBreakfast ? "Breakfast Included" : "Room Only",
                            source: "dom_table"
                        });
                    });
                }

                // Fallback to DOM cards
                if (rates.length === 0) {
                    const cards = Array.from(document.querySelectorAll("[data-testid='room-card'], div[data-testid='property-section--rooms'] > div"));
                    cards.forEach((card, idx) => {
                        const titleElem = card.querySelector("[data-testid='room-title'], h3, h4");
                        const curRoom = titleElem ? titleElem.innerText.trim() : `Room ${idx+1}`;
                        const txt = card.innerText;
                        const priceMatches = Array.from(txt.matchAll(/₹\\s*([0-9,]+)/g)).map(m => parseFloat(m[1].replace(/,/g, '')));
                        if (priceMatches.length === 0) return;
                        const base = priceMatches.find(p => p >= 2000) || priceMatches[0];
                        const isFreeCancel = /free cancellation/i.test(txt);
                        const hasBreakfast = /breakfast/i.test(txt);
                        const sel = card.querySelector('select');
                        const blockId = sel && sel.name ? sel.name.replace('nr_rooms_', '') : `card_${idx}`;
                        rates.push({
                            blockId: blockId,
                            roomName: curRoom,
                            occupancy: 2,
                            basePrice: base,
                            totalPrice: base * 1.18,
                            taxes: base * 0.18,
                            isFreeCancel: isFreeCancel,
                            mealPlan: hasBreakfast ? "Breakfast Included" : "Room Only",
                            source: "dom_card"
                        });
                    });
                }

                return { isSoldOut: false, rates: rates };
            }''')

            dur = (datetime.now(IST) - t0).total_seconds()
            await browser.close()

            if state.get("isSoldOut"):
                return {"hotel": name, "status": "blocked", "blocker": "sold_out", "rates": 0, "seconds": round(dur, 2)}
            
            rates = state.get("rates", [])
            return {
                "hotel": name,
                "status": "verified" if len(rates) > 0 else "unverified",
                "blocker": None if len(rates) > 0 else "other",
                "rates": len(rates),
                "cheapest": min((r["totalPrice"] for r in rates), default=None),
                "seconds": round(dur, 2),
                "sample": rates[0] if rates else None
            }
        except Exception as e:
            dur = (datetime.now(IST) - t0).total_seconds()
            await browser.close()
            return {"hotel": name, "status": "unverified", "blocker": "other", "rates": 0, "seconds": round(dur, 2), "error": str(e)}

async def main():
    results = []
    for name, url in HOTELS_6:
        res = await test_hotel(name, url)
        results.append(res)
        logger.info("HOTEL: %s -> %s (rates: %s, cheapest: %s, blocker: %s, time: %.2fs)",
                    name, res["status"], res["rates"], res.get("cheapest"), res.get("blocker"), res["seconds"])
        await asyncio.sleep(1.0)

    print("\n" + "=" * 90)
    print(f"{'Hotel':<32} | {'Status':<12} | {'Blocker':<10} | {'Rates':<8} | {'Cheapest':<10} | {'Sec':<6}")
    print("-" * 90)
    for r in results:
        blk = str(r.get("blocker"))
        chp = str(r.get("cheapest"))
        print(f"{r['hotel']:<32} | {r['status']:<12} | {blk:<10} | {r['rates']:<8} | {chp:<10} | {r['seconds']:<6.2f}")
    print("=" * 90)

    # Save to results
    out_file = Path("results/bookingcom_6hotels_validation.json")
    out_file.write_text(json.dumps(results, indent=2))
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    asyncio.run(main())
