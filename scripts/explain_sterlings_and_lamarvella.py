import asyncio
from playwright.async_api import async_playwright
import re

async def explain():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)

        # 1. Sterlings Mac on Nov 20-21 vs Nov 27-28
        print("=== STERLINGS MAC HOTEL ===")
        p1 = await b.new_page()
        await p1.goto("https://www.cleartrip.com/hotels/details/sterlings-mac-hotel-bengaluru-327940?c=201126%7C211126&r=2%2C0")
        await asyncio.sleep(4.0)
        await p1.screenshot(path="results/recon/sterlings_nov20_catalog.png")
        t1 = await p1.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book')).map(b => {
                let card = b.closest('div[class*="border"], div[class*="card"], div.p-4') || b.parentElement.parentElement;
                return card ? card.innerText.replace(/\\n+/g, ' | ') : '';
            });
        }""")
        print("Sterlings Mac Nov 20-21 rates:")
        for r in t1[:4]:
            print("  [Nov 20-21]", r[:140])

        p2 = await b.new_page()
        await p2.goto("https://www.cleartrip.com/hotels/details/sterlings-mac-hotel-bengaluru-327940?c=271126%7C281126&r=2%2C0")
        await asyncio.sleep(4.0)
        await p2.screenshot(path="results/recon/sterlings_nov27_catalog.png")
        t2 = await p2.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book')).map(b => {
                let card = b.closest('div[class*="border"], div[class*="card"], div.p-4') || b.parentElement.parentElement;
                return card ? card.innerText.replace(/\\n+/g, ' | ') : '';
            });
        }""")
        print("\nSterlings Mac Nov 27-28 rates:")
        for r in t2[:4]:
            print("  [Nov 27-28]", r[:140])

        # 2. La Marvella on Nov 20-21 vs Nov 27-28
        print("\n=== LA MARVELLA ===")
        p3 = await b.new_page()
        await p3.goto("https://www.cleartrip.com/hotels/details/la-marvella-2050898?c=201126%7C211126&r=2%2C0")
        await asyncio.sleep(4.0)
        await p3.screenshot(path="results/recon/lamarvella_nov20_catalog.png")
        t3 = await p3.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book')).map(b => {
                let card = b.closest('div[class*="border"], div[class*="card"], div.p-4') || b.parentElement.parentElement;
                return card ? card.innerText.replace(/\\n+/g, ' | ') : '';
            });
        }""")
        print("La Marvella Nov 20-21 rates:")
        for r in t3[:4]:
            print("  [Nov 20-21]", r[:140])

        p4 = await b.new_page()
        await p4.goto("https://www.cleartrip.com/hotels/details/la-marvella-2050898?c=271126%7C281126&r=2%2C0")
        await asyncio.sleep(4.0)
        await p4.screenshot(path="results/recon/lamarvella_nov27_catalog.png")
        t4 = await p4.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Book')).map(b => {
                let card = b.closest('div[class*="border"], div[class*="card"], div.p-4') || b.parentElement.parentElement;
                return card ? card.innerText.replace(/\\n+/g, ' | ') : '';
            });
        }""")
        print("\nLa Marvella Nov 27-28 rates:")
        for r in t4[:4]:
            print("  [Nov 27-28]", r[:140])

        await b.close()

if __name__ == "__main__":
    asyncio.run(explain())
