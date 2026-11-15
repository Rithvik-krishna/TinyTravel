import asyncio
from playwright.async_api import async_playwright
import re

async def test_submit():
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

        # Select 1 room
        sel = page.locator("#hprt-table tbody select").first
        await sel.select_option("1")
        await asyncio.sleep(1.0)

        # Click the submit button: button[type='submit'].js-reservation-button
        submit_btn = page.locator("button.js-reservation-button, button[type='submit'].hp_rt_input").first
        print("Submit button visible:", await submit_btn.is_visible())
        
        # Click and wait for navigation
        await submit_btn.click()
        await page.wait_for_url("**/book.html**", timeout=20000)
        print("Navigated to book.html! URL:", page.url)

        # Check step 1 (guest details)
        await page.fill("input[name='firstname'], input#firstname", "Test")
        await page.fill("input[name='lastname'], input#lastname", "Guest")
        await page.fill("input[name='email'], input#email", "test.guest+probe@example.com")
        await page.fill("input[name='phoneNumber'], input[name='phone'], input#phone", "9000000000")

        # Advance to step 2/3 (final details / payment)
        next_btn = page.locator("button[name='submit_step_1'], button:has-text('Next: Final details'), button:has-text('Next')").first
        await next_btn.click()
        await asyncio.sleep(5.0)

        print("After step 1 submit, URL:", page.url)
        # Parse final payable
        body_text = await page.evaluate("() => document.body.innerText")
        prices = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', body_text)
        print("Prices found on payment page:", prices[:10])

        await page.screenshot(path="results/recon/bookingcom_step_final.png", animations="disabled", timeout=15000)
        print("Saved screenshot to results/recon/bookingcom_step_final.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_submit())
