import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def inspect_hotel_discounts(hotel_url, hotel_name, device_type="desktop", locale="en-GB"):
    async with async_playwright() as p:
        if device_type == "mobile":
            device = p.devices["Pixel 7"]
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(**device, locale=locale)
        else:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                locale=locale,
                viewport={"width": 1280, "height": 800}
            )
        
        page = await context.new_page()
        try:
            await page.goto(hotel_url, wait_until="domcontentloaded", timeout=35000)
            await asyncio.sleep(4.0)
            
            # Extract all text, badges, banners related to discounts/genius/mobile
            data = await page.evaluate('''() => {
                const text = document.body ? document.body.innerText : '';
                const discounts = [];
                
                // Find all strike-through prices or discount labels
                const strikeEls = Array.from(document.querySelectorAll('del, [data-testid="price-and-discounted-price"] del, .bui-price-display__original, span[aria-hidden="true"]'));
                const badges = Array.from(document.querySelectorAll('[data-testid="badge"], .bui-badge, [class*="discount"], [class*="genius"]')).map(e => e.innerText.trim()).filter(Boolean);
                
                return {
                    url: window.location.href,
                    hasGenius: text.includes('Genius') || text.includes('genius'),
                    hasMobileRate: text.includes('Mobile-only') || text.includes('mobile price') || text.includes('Mobile rate'),
                    hasMemberRate: text.includes('Member') || text.includes('members-only') || text.includes('Sign in to get'),
                    badges: Array.from(new Set(badges)).slice(0, 10),
                    first1000Chars: text.substring(0, 1000)
                };
            }''')
            await browser.close()
            return {"hotel": hotel_name, "device": device_type, "locale": locale, "data": data}
        except Exception as e:
            await browser.close()
            return {"hotel": hotel_name, "device": device_type, "locale": locale, "error": str(e)}

async def main():
    rad_url = "https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
    bloom_url = "https://www.booking.com/hotel/in/bloomroom-cunninghamroad.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR"
    
    runs = [
        ("Radisson Blu Atria", rad_url, "desktop", "en-GB"),
        ("Radisson Blu Atria", rad_url, "mobile", "en-IN"),
        ("Bloomrooms City Centre", bloom_url, "desktop", "en-GB"),
        ("Bloomrooms City Centre", bloom_url, "mobile", "en-IN"),
    ]
    
    results = []
    for h_name, url, dev, loc in runs:
        print(f"Auditing {h_name} [{dev}, {loc}]...")
        res = await inspect_hotel_discounts(url, h_name, dev, loc)
        results.append(res)
        await asyncio.sleep(2.0)
        
    Path("results/recon/discount_eligibility_audit.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("Saved discount eligibility audit to results/recon/discount_eligibility_audit.json")

if __name__ == "__main__":
    asyncio.run(main())
