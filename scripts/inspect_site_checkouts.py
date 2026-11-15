import asyncio
import logging
from pathlib import Path
import re
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inspect_sites")

out_dir = Path("results/recon/site_inspections")
out_dir.mkdir(parents=True, exist_ok=True)

async def check_treebo(browser):
    logger.info(">>> Checking Treebo...")
    page = await browser.new_page()
    try:
        await page.goto("https://www.treebo.com/hotels-in-bangalore/", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)
        # Find hotel cards
        cards = page.locator("a[href*='/hotels-in-bangalore/']")
        count = await cards.count()
        logger.info("Treebo hotel cards count: %d", count)
        if count > 0:
            target_href = await cards.nth(2).get_attribute("href")
            logger.info("Target Treebo URL: %s", target_href)
            full_url = f"https://www.treebo.com{target_href}" if target_href.startswith("/") else target_href
            await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4.0)
            await page.screenshot(path=str(out_dir / "treebo_hotel_page.png"))
            
            # Look for Book button
            book_btn = page.locator("button:has-text('Book Now'), button:has-text('Select Room'), button:has-text('Book')").first
            if await book_btn.is_visible():
                await book_btn.click()
                await asyncio.sleep(3.0)
                await page.screenshot(path=str(out_dir / "treebo_after_book.png"))
                txt = await page.evaluate("() => document.body.innerText")
                logger.info("Treebo after book text: %s", txt[:300].replace("\n", " | "))
                # Check for login/OTP gate
                if "otp" in txt.lower() or "login" in txt.lower() or "sign in" in txt.lower() or "mobile number" in txt.lower():
                    logger.warning("Treebo has Login/OTP gate!")
            else:
                logger.warning("No Book button found on Treebo hotel page.")
    except Exception as e:
        logger.error("Treebo error: %s", e)
    finally:
        await page.close()

async def check_fabhotels(browser):
    logger.info(">>> Checking FabHotels...")
    page = await browser.new_page()
    try:
        await page.goto("https://www.fabhotels.com/hotels-in-bangalore", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)
        cards = page.locator("a[href*='/hotels-in-bangalore/']")
        count = await cards.count()
        logger.info("FabHotels cards count: %d", count)
        if count > 0:
            target_href = await cards.first.get_attribute("href")
            full_url = f"https://www.fabhotels.com{target_href}" if target_href.startswith("/") else target_href
            logger.info("Navigating to FabHotel: %s", full_url)
            await page.goto(full_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(4.0)
            await page.screenshot(path=str(out_dir / "fabhotels_hotel_page.png"))
            
            book_btn = page.locator("button:has-text('Book Now'), a:has-text('Book Now')").first
            if await book_btn.is_visible():
                await book_btn.click()
                await asyncio.sleep(4.0)
                await page.screenshot(path=str(out_dir / "fabhotels_after_book.png"))
                txt = await page.evaluate("() => document.body.innerText")
                logger.info("FabHotels after book text: %s", txt[:300].replace("\n", " | "))
            else:
                logger.warning("No Book button found on FabHotel page")
    except Exception as e:
        logger.error("FabHotels error: %s", e)
    finally:
        await page.close()

async def check_stayvista(browser):
    logger.info(">>> Checking StayVista...")
    page = await browser.new_page()
    try:
        await page.goto("https://www.stayvista.com/villas-in-bangalore", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)
        await page.screenshot(path=str(out_dir / "stayvista_search.png"))
        txt = await page.evaluate("() => document.body.innerText")
        logger.info("StayVista search text: %s", txt[:300].replace("\n", " | "))
    except Exception as e:
        logger.error("StayVista error: %s", e)
    finally:
        await page.close()

async def check_bookingcom_headed(browser):
    logger.info(">>> Checking Booking.com in headed mode...")
    page = await browser.new_page()
    try:
        url = "https://www.booking.com/hotel/in/treebo-trend-tiba.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4.0)
        await page.screenshot(path=str(out_dir / "bookingcom_headed_page.png"))
        txt = await page.evaluate("() => document.body.innerText")
        logger.info("Booking.com headed text: %s", txt[:300].replace("\n", " | "))
        # Check if reserve button is visible
        reserve_btn = page.locator("button:has-text('Reserve'), button:has-text('I\\'ll reserve'), a:has-text('Reserve')").first
        if await reserve_btn.is_visible():
            logger.info("Booking.com Reserve button is visible!")
        else:
            logger.warning("Booking.com Reserve button NOT visible")
    except Exception as e:
        logger.error("Booking.com headed error: %s", e)
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # Headed browser as requested for Booking.com & verification
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        await check_treebo(browser)
        await check_fabhotels(browser)
        await check_stayvista(browser)
        await check_bookingcom_headed(browser)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
