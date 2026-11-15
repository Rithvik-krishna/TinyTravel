import asyncio
from playwright.async_api import async_playwright
import re

async def test_booking_popup():
    url = "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)

        # Select 1 room in the table
        select_locator = page.locator("#hprt-table tbody tr select").first
        await select_locator.select_option("1")
        await asyncio.sleep(1.0)

        # Look for the reserve button that actually submits the form
        btn = page.locator("button.txp-bui-main-ppc-button, button[type='submit']:has-text('Reserve'), button:has-text('I\\'ll reserve'), button:has-text('Reserve')").first
        print("Reserve btn is visible:", await btn.is_visible())

        try:
            async with context.expect_page(timeout=10000) as pinfo:
                await btn.click()
            book_page = await pinfo.value
            print("Captured popup page URL:", book_page.url)
        except Exception as e:
            print("No popup event, checking open pages:", e)
            book_page = page
            for cp in context.pages:
                if "book.html" in cp.url:
                    book_page = cp
            print("Page URL:", book_page.url)

        await asyncio.sleep(5.0)
        print("After wait, book_page URL:", book_page.url)
        text = await book_page.evaluate("() => document.body.innerText")
        lines = [l.strip() for l in text.splitlines() if l.strip() and any(k in l.lower() for k in ["total", "price", "taxes", "₹", "inr"])]
        print("Found lines in book_page:", lines[:10])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_booking_popup())
