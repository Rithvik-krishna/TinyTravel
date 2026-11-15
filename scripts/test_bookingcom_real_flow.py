import asyncio
import logging
from pathlib import Path
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("booking_real")

async def run():
    url = "https://www.booking.com/hotel/in/treebo-trend-tiba.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
    logger.info("Opening Booking.com in headed mode: %s", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(4.0)
        await page.keyboard.press("Escape")

        # Check for room selection dropdowns
        selects = page.locator("select[data-testid='select-room-trigger'], select[name*='nr_rooms']")
        select_count = await selects.count()
        logger.info("Room select dropdown count: %d", select_count)
        if select_count > 0:
            await selects.first.select_option("1")
            logger.info("Selected 1 room in dropdown")
            await asyncio.sleep(1.0)

        # Click I'll reserve
        reserve_btn = page.locator("button:has-text('I\\'ll reserve'), button:has-text('Reserve'), button[type='submit']:has-text('Reserve')").first
        if await reserve_btn.is_visible():
            logger.info("Clicking Reserve button...")
            await reserve_btn.click()
            await asyncio.sleep(5.0)

        # Bring book.html to front if opened in new tab or same page
        book_page = page
        for p_curr in context.pages:
            if "book.html" in p_curr.url or "booking" in p_curr.url:
                book_page = p_curr
        await book_page.bring_to_front()
        logger.info("Current URL on book step: %s", book_page.url)

        out_dir = Path("results/recon/bookingcom_headed")
        out_dir.mkdir(parents=True, exist_ok=True)
        await book_page.screenshot(path=str(out_dir / "step1_guest_details.png"))

        # Look for guest inputs on book page
        text = await book_page.evaluate("() => document.body.innerText")
        logger.info("Book page text snippet: %s", text[:400].replace("\n", " | "))

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
