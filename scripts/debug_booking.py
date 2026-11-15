import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from playwright.async_api import async_playwright
import re

async def debug_booking():
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

        title = await page.title()
        print("Page title:", title)
        html = await page.content()

        # Real challenge checks:
        if "px-captcha" in html or "press & hold" in html.lower() or "access denied" in title.lower():
            print("Real CAPTCHA detected!")
            await browser.close()
            return

        # Look for price texts or table
        matches = re.findall(r'₹\s*([0-9,]+)', html)
        print("Found price matches:", matches[:10])

        # Check room table elements
        tables = await page.query_selector_all("#hprt-table, table.hprt-table, .roomstable, [data-block-id='room_table']")
        print("Room tables found:", len(tables))

        # Check select boxes
        selects = await page.query_selector_all("select")
        print("Select elements found:", len(selects))
        for s in selects[:5]:
            name = await s.get_attribute("name")
            testid = await s.get_attribute("data-testid")
            print("Select:", name, testid)

        # Check reserve buttons
        buttons = await page.query_selector_all("button, a.bui-button, [data-testid='reserve-button']")
        reserve_btns = []
        for b in buttons:
            txt = await b.inner_text()
            if "reserve" in txt.lower() or "book" in txt.lower() or "i'll reserve" in txt.lower():
                reserve_btns.append(txt.strip())
        print("Reserve buttons found:", reserve_btns[:5])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_booking())
