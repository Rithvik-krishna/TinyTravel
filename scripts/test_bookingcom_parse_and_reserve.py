import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from playwright.async_api import async_playwright
import re

async def test_booking():
    url = "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)

        # Parse table rows and find cheapest free-cancellation for 2 adults
        rate_info = await page.evaluate('''() => {
            const table = document.querySelector('#hprt-table, table.hprt-table');
            if (!table) return null;
            const trs = Array.from(table.querySelectorAll('tbody tr'));
            let currentRoomName = "Standard Room";
            const rates = [];

            trs.forEach((tr, idx) => {
                const roomHeader = tr.querySelector('.hprt-roomtype-link, .hprt-roomtype-icon-link, .room-name');
                if (roomHeader) {
                    currentRoomName = roomHeader.innerText.trim();
                }
                const text = tr.innerText;
                const select = tr.querySelector('select');
                if (!select) return;

                const isFreeCancel = /free cancellation/i.test(text);
                const hasBreakfast = /breakfast included/i.test(text);
                const is2Adults = /max.*people.*2|2 adults/i.test(text) || true;

                // Extract prices
                const priceMatches = Array.from(text.matchAll(/₹\\s*([0-9,]+)/g)).map(m => parseFloat(m[1].replace(/,/g, '')));
                if (priceMatches.length === 0) return;

                // Usually in Booking.com row: first is base rate, then taxes
                const basePrice = Math.min(...priceMatches);
                rates.push({
                    rowIdx: idx,
                    roomName: currentRoomName,
                    isFreeCancel: isFreeCancel,
                    hasBreakfast: hasBreakfast,
                    basePrice: basePrice,
                    textSnippet: text.slice(0, 100).replace(/\\n/g, ' ')
                });
            });
            return rates;
        }''')

        print("Parsed rates count:", len(rate_info) if rate_info else 0)
        if rate_info:
            for r in rate_info[:5]:
                print(r)

            # Filter free cancel
            free_cancels = [r for r in rate_info if r["isFreeCancel"]]
            target = min(free_cancels, key=lambda x: x["basePrice"]) if free_cancels else rate_info[0]
            print("Selected target rate:", target)

            # Select 1 room in that row's dropdown
            row_idx = target["rowIdx"]
            select_locator = page.locator(f"#hprt-table tbody tr:nth-child({row_idx + 1}) select, table.hprt-table tbody tr:nth-child({row_idx + 1}) select").first
            await select_locator.select_option("1")
            await asyncio.sleep(1.0)

            # Click reserve button
            btn = page.locator("button:has-text('I\\'ll reserve'), button:has-text('Reserve')").first
            await btn.click()
            await asyncio.sleep(5.0)

            # Check open pages for book.html
            book_page = page
            for cp in context.pages:
                if "book.html" in cp.url:
                    book_page = cp
                    break
            await book_page.bring_to_front()
            print("Current URL after reserve:", book_page.url)

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

            next_btn = book_page.locator("button[name='submit_step_1'], button:has-text('Next: Final details'), button:has-text('Next')").first
            if await next_btn.is_visible():
                await next_btn.click()
                await asyncio.sleep(5.0)

            print("Final page URL:", book_page.url)
            fin_text = await book_page.evaluate("() => document.body.innerText")
            prices_fin = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', fin_text)
            print("Prices on final page:", prices_fin[:5])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_booking())
