import asyncio
import logging
from pathlib import Path
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("booking_step2")

async def run():
    url = "https://www.booking.com/hotel/in/treebo-trend-tiba.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
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

        selects = page.locator("select[data-testid='select-room-trigger'], select[name*='nr_rooms']")
        if await selects.count() > 0:
            await selects.first.select_option("1")
        reserve_btn = page.locator("button:has-text('I\\'ll reserve'), button:has-text('Reserve')").first
        await reserve_btn.click()
        await asyncio.sleep(5.0)

        book_page = page
        for p_curr in context.pages:
            if "book.html" in p_curr.url:
                book_page = p_curr
        await book_page.bring_to_front()

        # Fill inputs
        # Booking.com uses firstname, lastname, email, phone
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

        logger.info("Filled guest details on Booking.com book page")

        # Click Next: Final details
        next_btn = book_page.locator("button[name='submit_step_1'], button:has-text('Next: Final details'), button:has-text('Next')").first
        if await next_btn.is_visible():
            logger.info("Clicking Next: Final details button...")
            await next_btn.click()
            await asyncio.sleep(5.0)

        out_dir = Path("results/recon/bookingcom_headed")
        out_dir.mkdir(parents=True, exist_ok=True)
        await book_page.screenshot(path=str(out_dir / "step2_final_details.png"))

        txt = await book_page.evaluate("() => document.body.innerText")
        logger.info("Final step URL: %s", book_page.url)
        logger.info("Text sample on payment step: %s", txt[:500].replace("\n", " | "))

        # Extract prices
        prices = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', txt)
        clean = [float(p.replace(",", "")) for p in prices]
        logger.info("Found prices: %s", clean[:10])

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
