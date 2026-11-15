import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

RECON_DIR = Path("results/recon")
RECON_DIR.mkdir(parents=True, exist_ok=True)

async def capture_site(site_name: str, start_url: str, search_query: str):
    site_recon_dir = RECON_DIR / site_name
    site_recon_dir.mkdir(parents=True, exist_ok=True)
    har_path = RECON_DIR / f"{site_name}_recon.har"
    
    print(f"\n--- Starting {site_name} Recon ---")
    print(f"URL: {start_url}")
    print(f"HAR path: {har_path}")

    json_counter = 0
    captured_endpoints = []

    async with async_playwright() as p:
        # Launch browser (we can test headed=True or headed=False)
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = await browser.new_context(
            record_har_path=str(har_path),
            record_har_content="embed",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )

        page = await context.new_page()

        async def handle_response(response):
            nonlocal json_counter
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct or "text/json" in ct or "json" in ct:
                    url = response.url
                    status = response.status
                    try:
                        data = await response.json()
                    except Exception:
                        text = await response.text()
                        try:
                            data = json.loads(text)
                        except Exception:
                            return

                    json_counter += 1
                    parsed = urlparse(url)
                    path_slug = re.sub(r"[^a-zA-Z0-9_-]", "_", parsed.path.strip("/"))
                    if not path_slug:
                        path_slug = "root"
                    filename = f"{json_counter:03d}_{parsed.netloc}_{path_slug[:40]}.json"
                    filepath = site_recon_dir / filename

                    record = {
                        "url": url,
                        "status": status,
                        "content_type": ct,
                        "headers": dict(response.headers),
                        "data": data,
                    }
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(record, f, indent=2, ensure_ascii=False)

                    captured_endpoints.append({
                        "id": json_counter,
                        "url": url,
                        "file": filename,
                        "status": status
                    })
                    print(f"  [{site_name}] Captured JSON #{json_counter}: {parsed.path[:60]}")
            except Exception as e:
                pass

        page.on("response", handle_response)

        try:
            print(f"Navigating to {start_url}...")
            await page.goto(start_url, timeout=60000, wait_until="networkidle")
            await asyncio.sleep(5)
            
            # Save screenshot of initial load
            screenshot_path = site_recon_dir / "initial_page.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"Initial screenshot saved to {screenshot_path}")

            # Check page title and content
            title = await page.title()
            print(f"Page title: {title}")
            page_text = await page.content()
            
            # Check for bot block
            if any(term in page_text.lower() for term in ["captcha", "challenge", "cf-ray", "access denied", "please verify", "security check", "perimeterx"]):
                print(f"WARNING: Bot detection or challenge detected on {site_name}")
            else:
                print(f"No immediate bot blocker detected on {site_name}")

            # Try interacting / searching for Radisson Blu Atria Bengaluru if needed
            print(f"Interacting to locate {search_query}...")
            # Let page settle
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Error during {site_name} recon: {e}")
        finally:
            await context.close()
            await browser.close()

    print(f"Completed {site_name}: captured {json_counter} JSON responses.")
    # Save index
    index_file = site_recon_dir / "endpoints_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(captured_endpoints, f, indent=2)
    print(f"Saved index to {index_file}")

async def main():
    # 1. Cleartrip
    ct_url = "https://www.cleartrip.com/hotels/results?city=Bengaluru&chk_in=2026-11-20&chk_out=2026-11-21&adults=2&num_rooms=1"
    await capture_site("cleartrip", ct_url, "Radisson Blu Atria Bengaluru")

    # 2. Agoda
    agoda_url = "https://www.agoda.com/search?city=Bengaluru&checkIn=2026-11-20&checkOut=2026-11-21&rooms=1&adults=2&currency=INR"
    await capture_site("agoda", agoda_url, "Radisson Blu Atria Bengaluru")

if __name__ == "__main__":
    asyncio.run(main())
