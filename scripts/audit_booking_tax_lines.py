import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from api.agents.playbooks.bookingcom import KNOWN_BOOKING_HOTELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_booking_tax")
IST = timezone(timedelta(hours=5, minutes=30))

HOTELS = [
    ("Bloomrooms City Centre", "bloomrooms city centre"),
    ("ibis Bengaluru City Centre", "ibis bengaluru city centre"),
    ("Radisson Blu Atria Bengaluru", "radisson blu atria bengaluru"),
    ("The Oberoi Bengaluru", "the oberoi bengaluru"),
    ("Sterlings Mac Hotel", "sterlings mac hotel"),
    ("Treebo Tiba", "treebo tiba"),
]

async def audit_hotel(display_name: str, hotel_key: str, cin: str = "2026-11-20", cout: str = "2026-11-21"):
    url_base = KNOWN_BOOKING_HOTELS.get(hotel_key)
    target_url = f"{url_base}?checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1&selected_currency=INR&lang=en-gb"
    
    logger.info(">>> Auditing Booking.com for: %s | URL: %s", display_name, target_url)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 1000},
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"}
        )
        page = await ctx.new_page()
        await page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
        await asyncio.sleep(4.0)

        # Handle redirect param strip
        if "searchresults" in page.url or "checkin" not in page.url:
            logger.info("Redirect stripped params, using search flow...")
            encoded_q = hotel_key.replace(" ", "+")
            search_url = f"https://www.booking.com/searchresults.en-gb.html?ss={encoded_q}&checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1&selected_currency=INR"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(3.0)
            card = await page.query_selector('a[data-testid="title-link"]')
            if card:
                href = await card.get_attribute("href")
                if href:
                    await page.goto(href, wait_until="domcontentloaded", timeout=35000)
                    await asyncio.sleep(3.0)

        # Step 2: Select room
        select_elem = await page.query_selector('select[data-testid="select-room-trigger"]')
        if select_elem:
            await select_elem.select_option("1")
            await asyncio.sleep(1.0)
        
        reserve_btn = await page.query_selector('button[id="b_tt_holder_1"], button:has-text("I\'ll reserve"), button:has-text("Reserve")')
        if reserve_btn:
            await reserve_btn.click()
            await asyncio.sleep(5.0)

        # Check pages in context
        book_page = page
        for p_curr in ctx.pages:
            if "book.html" in p_curr.url:
                book_page = p_curr
                break
        
        # If on stage 1 (Your details), fill guest details and click Next to reach stage 2 (Finish booking)
        for stage in [1, 2]:
            inputs = await book_page.locator("input").all()
            for inp in inputs:
                try:
                    name_attr = await inp.get_attribute("name") or ""
                    type_attr = await inp.get_attribute("type") or ""
                    if "firstname" in name_attr.lower() or name_attr == "firstname":
                        await inp.fill("Test")
                    elif "lastname" in name_attr.lower() or name_attr == "lastname":
                        await inp.fill("Guest")
                    elif "email" in name_attr.lower() or type_attr == "email":
                        await inp.fill("test.guest+probe@example.com")
                    elif "phone" in name_attr.lower() or type_attr == "tel":
                        await inp.fill("9000000000")
                except Exception:
                    pass

            next_btn = await book_page.query_selector('button[name="book"], button:has-text("Next: Final details"), button:has-text("Next: final details"), button:has-text("Continue")')
            if next_btn:
                try:
                    await next_btn.click()
                    await asyncio.sleep(4.0)
                except Exception:
                    pass

        # Extract full page text and structured price breakdown
        full_text = await book_page.evaluate("() => document.body ? document.body.innerText : ''")
        
        # Extract price breakdown box specifically
        breakdown_data = await book_page.evaluate('''() => {
            const res = {
                price_box_text: "",
                all_inr_lines: []
            };
            // Look for price summary elements
            const summaryBox = document.querySelector('[data-testid="price-summary"], [class*="price-summary"], [class*="PriceSummary"], aside[class*="summary"], [class*="bp-overview__price"]');
            if (summaryBox) {
                res.price_box_text = summaryBox.innerText;
            }

            // Extract all elements mentioning ₹
            document.querySelectorAll('*').forEach(el => {
                const t = (el.innerText || '').trim();
                if (t.includes('₹') && t.length < 100 && !t.includes('\\n')) {
                    res.all_inr_lines.push(t);
                }
            });
            res.all_inr_lines = Array.from(new Set(res.all_inr_lines));
            return res;
        }''')

        # Save full_page screenshot and text
        out_dir = Path("results/recon/tax_audit")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = hotel_key.replace(" ", "_")
        
        scr_path = out_dir / f"bookingcom_{slug}_{cin}_fullpage.png"
        await book_page.screenshot(path=str(scr_path), full_page=True)

        txt_path = out_dir / f"bookingcom_{slug}_{cin}_page.txt"
        txt_path.write_text(full_text, encoding="utf-8")

        box_path = out_dir / f"bookingcom_{slug}_{cin}_pricebox.txt"
        box_path.write_text(breakdown_data["price_box_text"], encoding="utf-8")

        logger.info("Saved full_page screenshot to %s and text to %s", scr_path, txt_path)

        await browser.close()

        return {
            "hotel": display_name,
            "url": book_page.url,
            "price_box": breakdown_data["price_box_text"],
            "inr_lines": breakdown_data["all_inr_lines"],
            "full_text": full_text
        }

async def main():
    results = {}
    for disp, key in HOTELS:
        res = await audit_hotel(disp, key)
        results[disp] = res
        await asyncio.sleep(2.0)

    # Save summary
    out_summary = Path("results/recon/tax_audit/booking_tax_audit_summary.json")
    # Save without full_text to keep file compact
    compact = {k: {"hotel": v["hotel"], "url": v["url"], "price_box": v["price_box"], "inr_lines": v["inr_lines"]} for k, v in results.items()}
    out_summary.write_text(json.dumps(compact, indent=2), encoding="utf-8")
    logger.info("All 6 hotels audited for Booking.com tax breakdown!")

if __name__ == "__main__":
    asyncio.run(main())
