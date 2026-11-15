import asyncio
import json
import re
from playwright.async_api import async_playwright

async def get_hotels():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        url = "https://www.cleartrip.com/hotels/results?city=Bengaluru&chk_in=2026-11-20&chk_out=2026-11-21&adults=2&num_rooms=1"
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4.0)
        await page.keyboard.press("Escape")
        
        # Scroll down slightly to trigger loading more cards
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.0)

        # Extract hotel links
        hrefs = await page.eval_on_selector_all("a[href*='/hotels/details/']", "elements => elements.map(e => ({href: e.href, text: e.innerText}))")
        print(f"Total links found: {len(hrefs)}")
        seen = set()
        hotels = []
        for l in hrefs:
            m = re.search(r'/hotels/details/([^?]+)', l["href"])
            if m:
                slug = m.group(1)
                if slug not in seen:
                    seen.add(slug)
                    first_line = l["text"].splitlines()[0].strip() if l["text"] else ""
                    hotels.append({"slug": slug, "href": l["href"], "name": first_line})

        print(f"Unique hotel slugs: {len(hotels)}")
        for h in hotels:
            print(f"SLUG: {h['slug']} | NAME: {h['name']}")
            
        with open("results/cleartrip_discovered_hotels.json", "w", encoding="utf-8") as f:
            json.dump(hotels, f, indent=2)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_hotels())
