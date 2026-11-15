import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sys

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("la_marvella")

async def run():
    out_dir = Path("results/recon/cleartrip")
    out_dir.mkdir(parents=True, exist_ok=True)

    url = "https://www.cleartrip.com/hotels/details/la-marvella-2050898?c=201126%7C211126&r=2%2C0"
    logger.info("Starting La Marvella breakdown inspection: %s", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(4.0)
        await page.keyboard.press("Escape")

        book_btns = page.locator("button:has-text('Book')")
        btn_count = await book_btns.count()
        logger.info("Found %d Book buttons for La Marvella", btn_count)

        if btn_count > 0:
            await book_btns.first.click()
            await asyncio.sleep(5.0)

        itin_page = page
        for p_curr in context.pages:
            if "itinerary" in p_curr.url:
                itin_page = p_curr
                break
        await itin_page.bring_to_front()
        await asyncio.sleep(3.0)

        # Fill traveller details
        inputs = await itin_page.locator("input").all()
        if len(inputs) >= 4:
            await inputs[0].fill("Test")
            await inputs[1].fill("Guest")
            await inputs[2].fill("test.guest+probe@example.com")
            await inputs[3].fill("9000000000")
            logger.info("Filled traveller details for La Marvella")

        continue_btn = itin_page.locator("button:has-text('Continue to payment')").first
        if await continue_btn.is_visible():
            await continue_btn.click()
            await asyncio.sleep(5.0)

        # Payment review step
        html = await itin_page.content()
        (out_dir / "la_marvella_payment_page.html").write_text(html, encoding="utf-8")
        
        scr_path = out_dir / "la_marvella_breakdown.png"
        await itin_page.screenshot(path=str(scr_path), full_page=False)
        logger.info("Saved La Marvella breakdown screenshot to %s", scr_path)

        # Extract price breakdown breakdown elements
        breakdown_items = await itin_page.evaluate("""() => {
            const items = [];
            // Look for price breakdown table rows or cards
            document.querySelectorAll('div, tr, li, p').forEach(el => {
                const txt = el.innerText || '';
                if (txt.includes('₹') && txt.length < 100 && !txt.includes('\\n')) {
                    items.push(txt.trim());
                }
            });
            // Also get buttons or headings with Total
            const totals = [];
            document.querySelectorAll('button, h1, h2, h3, h4, div').forEach(el => {
                const t = el.innerText || '';
                if ((t.toLowerCase().includes('total') || t.toLowerCase().includes('pay')) && t.includes('₹') && t.length < 50) {
                    totals.push(t.trim());
                }
            });
            return { items: Array.from(new Set(items)), totals: Array.from(new Set(totals)) };
        }""")

        (out_dir / "la_marvella_breakdown_data.json").write_text(json.dumps(breakdown_items, indent=2), encoding="utf-8")
        logger.info("Extracted %d items, %d totals", len(breakdown_items["items"]), len(breakdown_items["totals"]))
        print("TOTAL CANDIDATES:", breakdown_items["totals"])
        print("SAMPLE BREAKDOWN ITEMS:", breakdown_items["items"][:10])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
