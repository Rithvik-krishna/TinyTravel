import asyncio
import logging
from pathlib import Path
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inspect_treebo")

async def test_treebo():
    url = "https://www.treebo.com/hotels-in-bangalore/treebo-trend-tiba-indiranagar-1748/?checkin=2026-11-20&checkout=2026-11-21&rooms=1&adults=2"
    logger.info("Opening Treebo: %s", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(4.0)

        # Look for Book Now buttons
        btns = await page.locator("button, a").all()
        book_candidates = []
        for b in btns:
            try:
                txt = (await b.inner_text()).strip()
                if "book" in txt.lower() or "select" in txt.lower():
                    book_candidates.append(txt)
            except Exception:
                pass
        logger.info("Book candidates on Treebo: %s", book_candidates)

        # Click the primary Book Now button
        book_btn = page.locator("button:has-text('Book'), a:has-text('Book')").first
        if await book_btn.is_visible():
            logger.info("Clicking book button...")
            await book_btn.click()
            await asyncio.sleep(4.0)

        curr_url = page.url
        logger.info("After click, current URL: %s", curr_url)

        # Check what is on the page (Login / OTP modal? Or Guest details form?)
        body_text = await page.evaluate("() => document.body.innerText")
        logger.info("Page text sample: %s", body_text[:400].replace("\n", " | "))

        out_dir = Path("results/recon/treebo_inspect")
        out_dir.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_dir / "after_book_click.png"))

        # Look for OTP, Login, Mobile inputs
        inputs = await page.locator("input").all()
        input_info = []
        for inp in inputs:
            try:
                placeholder = await inp.get_attribute("placeholder")
                name = await inp.get_attribute("name")
                typ = await inp.get_attribute("type")
                input_info.append({"placeholder": placeholder, "name": name, "type": typ})
            except Exception:
                pass
        logger.info("Inputs on page: %s", input_info)

        has_otp = "otp" in body_text.lower() or "verification code" in body_text.lower()
        has_login = "login" in body_text.lower() or "sign in" in body_text.lower() or "send otp" in body_text.lower()
        logger.info("Has OTP: %s, Has Login: %s", has_otp, has_login)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_treebo())
