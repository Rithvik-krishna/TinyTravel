import asyncio
import json
import logging
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.async_api import async_playwright
from api.agents.playbooks.bookingcom import KNOWN_BOOKING_HOTELS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_booking_tax")

HOTELS_TO_TEST = [
    ("Bloomrooms City Centre", "bloomrooms city centre"),
    ("ibis Bengaluru City Centre", "ibis bengaluru city centre"),
    ("Radisson Blu Atria Bengaluru", "radisson blu atria bengaluru"),
    ("The Oberoi Bengaluru", "the oberoi bengaluru"),
    ("Sterlings Mac Hotel", "sterlings mac hotel"),
    ("Treebo Tiba", "treebo tiba"),
]

async def inspect_hotel(display_name: str, hotel_key: str, cin: str = "2026-11-20", cout: str = "2026-11-21"):
    url_base = KNOWN_BOOKING_HOTELS.get(hotel_key)
    target_url = f"{url_base}?checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1&selected_currency=INR&lang=en-gb"
    
    logger.info(">>> Inspecting: %s", display_name)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 900},
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"}
        )
        page = await ctx.new_page()
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3.0)

            # Check for redirect param stripping
            if "searchresults" in page.url or "checkin" not in page.url:
                logger.info("Search fallback for %s", hotel_key)
                q = hotel_key.replace(" ", "+")
                s_url = f"https://www.booking.com/searchresults.en-gb.html?ss={q}&checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1&selected_currency=INR"
                await page.goto(s_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3.0)
                card = await page.query_selector('a[data-testid="title-link"]')
                if card:
                    h = await card.get_attribute("href")
                    if h:
                        await page.goto(h, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(3.0)

            # Select 1 room
            selects = await page.query_selector_all('select[data-testid="select-room-trigger"], select.hprt-nos-select')
            if selects:
                await selects[0].select_option("1")
                await asyncio.sleep(1.0)
            
            reserve = await page.query_selector('button[id="b_tt_holder_1"], button:has-text("I\'ll reserve"), button:has-text("Reserve")')
            if reserve:
                await reserve.click()
                await asyncio.sleep(4.0)

            book_page = page
            for p_c in ctx.pages:
                if "book.html" in p_c.url:
                    book_page = p_c
                    break
            await book_page.bring_to_front()

            # Fill details if on step 1
            fn = await book_page.query_selector("input[name='firstname'], input#firstname")
            if fn:
                await fn.fill("Test")
            ln = await book_page.query_selector("input[name='lastname'], input#lastname")
            if ln:
                await ln.fill("Guest")
            em = await book_page.query_selector("input[name='email'], input#email")
            if em:
                await em.fill("test.guest+probe@example.com")
            ph = await book_page.query_selector("input[name='phoneNumber'], input[name='phone'], input#phone")
            if ph:
                await ph.fill("9000000000")

            nxt = await book_page.query_selector('button[name="submit_step_1"], button:has-text("Next: Final details"), button:has-text("Next")')
            if nxt:
                await nxt.click()
                await asyncio.sleep(4.0)

            # Price box extraction
            info = await book_page.evaluate('''() => {
                const bodyText = document.body ? document.body.innerText : '';
                
                // Specific price breakdown containers
                const priceElements = Array.from(document.querySelectorAll('[data-testid="price-summary"], [class*="price-summary"], [class*="PriceSummary"], aside, [class*="bp-overview__price"]'));
                let summaryBoxText = "";
                if (priceElements.length > 0) {
                    summaryBoxText = priceElements.map(e => e.innerText).join('\\n---\\n');
                }
                
                return {
                    url: window.location.href,
                    bodyText: bodyText,
                    summaryBoxText: summaryBoxText
                };
            }''')

            out_dir = Path("results/recon/tax_audit")
            out_dir.mkdir(parents=True, exist_ok=True)
            slug = hotel_key.replace(" ", "_")

            # Screenshot full page
            scr = out_dir / f"bookingcom_{slug}_{cin}_fullpage.png"
            await book_page.screenshot(path=str(scr), full_page=True)

            txt_file = out_dir / f"bookingcom_{slug}_{cin}_page.txt"
            txt_file.write_text(info["bodyText"], encoding="utf-8")

            box_file = out_dir / f"bookingcom_{slug}_{cin}_pricebox.txt"
            box_file.write_text(info["summaryBoxText"], encoding="utf-8")

            logger.info("Successfully audited %s | Saved screenshot %s", display_name, scr)
            return {
                "hotel": display_name,
                "url": info["url"],
                "screenshot": str(scr),
                "text_file": str(txt_file),
                "box_file": str(box_file)
            }
        except Exception as e:
            logger.error("Error auditing %s: %s", display_name, e)
            return {"hotel": display_name, "error": str(e)}
        finally:
            await browser.close()

async def main():
    results = []
    for disp, key in HOTELS_TO_TEST:
        r = await inspect_hotel(disp, key)
        results.append(r)
        await asyncio.sleep(2.0)
    Path("results/recon/tax_audit/audit_index.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

if __name__ == "__main__":
    asyncio.run(main())
