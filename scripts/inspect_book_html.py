import asyncio
from playwright.async_api import async_playwright

async def inspect_book_html():
    url = 'https://www.booking.com/hotel/in/radisson-blu-atria-bengaluru.html?checkin=2026-11-20&checkout=2026-11-21&group_adults=2&no_rooms=1&selected_currency=INR'
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False)
        ctx = await b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
        page = await ctx.new_page()
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(4.0)

        # Select room
        sel = page.locator('#hprt-table tbody select').first
        await sel.select_option('1')
        await asyncio.sleep(1.0)
        btn = page.locator("button:has-text('Reserve')").first
        await btn.click()
        await asyncio.sleep(5.0)

        book_page = page
        for cp in ctx.pages:
            if 'book.html' in cp.url:
                book_page = cp
        print('Book page URL:', book_page.url)
        content = await book_page.content()
        print('Book page HTML len:', len(content))
        lines = (await book_page.evaluate('() => document.body.innerText')).splitlines()
        for l in lines:
            if any(k in l.lower() for k in ['total', 'price', 'tax', 'inr', '₹', 'pay']):
                print('LINE:', l.strip())
        await b.close()

if __name__ == '__main__':
    asyncio.run(inspect_book_html())
