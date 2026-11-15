import asyncio
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sys

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ct_dates")

# 3 different dates in Nov 2026 and Dec 2026:
# Date 1: 2026-11-20 to 2026-11-21 (c=201126|211126)
# Date 2: 2026-11-27 to 2026-11-28 (c=271126|281126)
# Date 3: 2026-12-15 to 2026-12-16 (c=151226|161226)
TEST_DATES = [
    {"cin": "2026-11-20", "cout": "2026-11-21", "c_param": "201126|211126", "label": "Date 1 (Nov 20-21)"},
    {"cin": "2026-11-27", "cout": "2026-11-28", "c_param": "271126|281126", "label": "Date 2 (Nov 27-28)"},
    {"cin": "2026-12-15", "cout": "2026-12-16", "c_param": "151226|161226", "label": "Date 3 (Dec 15-16)"},
]

HOTEL_SLUG = "radisson-blu-atria-bengaluru-2043762"
HOTEL_NAME = "Radisson Blu Atria Bengaluru"

async def test_date_run(p, date_info, run_idx):
    cin = date_info["cin"]
    cout = date_info["cout"]
    c_param = date_info["c_param"].replace("|", "%7C")
    label = date_info["label"]

    url = f"https://www.cleartrip.com/hotels/details/{HOTEL_SLUG}?c={c_param}&r=2%2C0"
    logger.info(">>> Testing Date Run %d: %s | URL: %s", run_idx, label, url)

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

    out_dir = Path("results/recon/cleartrip_dates")
    out_dir.mkdir(parents=True, exist_ok=True)

    await page.goto(url, wait_until="domcontentloaded", timeout=40000)
    await asyncio.sleep(4.0)
    await page.keyboard.press("Escape")

    # Capture details page dates text
    details_text = await page.evaluate("() => document.body.innerText")
    
    # Locate book buttons
    book_btns = page.locator("button:has-text('Book')")
    btn_count = await book_btns.count()
    logger.info("Found %d Book buttons on details page", btn_count)

    rate_data = await page.evaluate("""() => {
        const results = [];
        const buttons = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book'));
        buttons.forEach((btn, idx) => {
            let container = btn.closest('div[class*="flex"], div[data-testid], tr') || btn.parentElement.parentElement;
            let text = container ? container.innerText : '';
            let parentCard = btn.closest('div[class*="border"], div[class*="card"], div.p-4') || container.parentElement;
            let cardText = parentCard ? parentCard.innerText : text;
            results.push({
                index: idx,
                text: text,
                cardText: cardText
            });
        });
        return results;
    }""")

    # Click first book button
    if btn_count > 0:
        await book_btns.first.click()
        await asyncio.sleep(5.0)

    # Check for itinerary page
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
        logger.info("Filled traveller details")

    continue_btn = itin_page.locator("button:has-text('Continue to payment')").first
    if await continue_btn.is_visible():
        await continue_btn.click()
        await asyncio.sleep(5.0)

    # Now on payment review step
    itin_text = await itin_page.evaluate("() => document.body.innerText")
    scr_path = out_dir / f"run_{run_idx}_payment_page.png"
    await itin_page.screenshot(path=str(scr_path), full_page=False)
    logger.info("Saved screenshot to %s", scr_path)

    # Search for dates and amounts on payment page
    # Dates usually appear as "20 Nov - 21 Nov" or "Fri, 20 Nov - Sat, 21 Nov" or similar
    date_matches = re.findall(r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)?,?\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^,\n\r]{0,30}', itin_text)
    
    # Extract price breakdown
    prices = re.findall(r'₹\s*([0-9,]+(?:\.[0-9]+)?)', itin_text)
    clean_prices = [float(p.replace(",", "")) for p in prices]

    await browser.close()

    return {
        "run_index": run_idx,
        "label": label,
        "check_in": cin,
        "check_out": cout,
        "url": url,
        "screenshot": str(scr_path),
        "observed_dates_sample": date_matches[:5],
        "prices_sample": clean_prices[:10],
        "max_price": max(clean_prices) if clean_prices else None,
        "min_price": min(clean_prices) if clean_prices else None,
        "page_snippet": itin_text[:500].replace("\n", " "),
    }

async def main():
    results = []
    async with async_playwright() as p:
        for idx, d in enumerate(TEST_DATES, 1):
            res = await test_date_run(p, d, idx)
            results.append(res)

    out_file = Path("results/cleartrip_dates_test.json")
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    logger.info("Date test completed. Saved to %s", out_file)

if __name__ == "__main__":
    asyncio.run(main())
