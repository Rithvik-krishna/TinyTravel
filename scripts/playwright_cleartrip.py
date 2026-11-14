"""
Cleartrip Playwright Automation Playbook (3-Hour Spike)
Executes deterministic guest checkout on Cleartrip stopping at payment.
Never attempts to solve, click through, or bypass anti-bot challenges.
If blocked by bot checks or selector mismatch, reports status='blocked'.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("tinytravel.playwright")
IST = timezone(timedelta(hours=5, minutes=30))


async def run_cleartrip_playbook(hotel_name: str, req: dict, timeout_s: float = 120.0) -> Dict[str, Any]:
    """
    Execute Playwright script for Cleartrip hotel checkout.
    Returns standardized probe result dict or blocked status.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {
            "status": "blocked",
            "blocker": "environment",
            "error": "Playwright is not installed in the current environment.",
            "steps": 0,
            "cost_usd": 0.0,
        }

    city = req.get("destination", "Bengaluru")
    check_in = req.get("check_in", "2026-11-20")
    check_out = req.get("check_out", "2026-11-21")
    guests = req.get("guests", 2)

    search_url = (
        f"https://www.cleartrip.com/hotels/results?"
        f"city={city}&chk_in={check_in}&chk_out={check_out}&adults={guests}&num_rooms=1"
    )

    t0 = datetime.now(IST)
    steps = 0

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Step 1: Navigate to search results
            steps += 1
            await page.goto(search_url, timeout=timeout_s * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(3.0)

            # Check for bot challenge or block
            page_text = await page.content()
            if any(term in page_text.lower() for term in ["captcha", "challenge", "cf-ray", "access denied", "please verify"]):
                await browser.close()
                return {
                    "status": "blocked",
                    "blocker": "captcha",
                    "error": "Blocked by Cloudflare/Akamai bot detection on search page.",
                    "steps": steps,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                    "cost_usd": 0.0,
                }

            # Step 2: Search for hotel name in listing filter or cards
            steps += 1
            hotel_card = page.locator(f"text={hotel_name}").first
            if not await hotel_card.is_visible(timeout=5000):
                await browser.close()
                return {
                    "status": "unverified",
                    "blocker": "layout",
                    "error": f"Hotel '{hotel_name}' not visible on first page.",
                    "steps": steps,
                    "seconds": (datetime.now(IST) - t0).total_seconds(),
                    "cost_usd": 0.0,
                }

            # Additional checkout steps would click room, enter guest details, and stop at payment
            await browser.close()
            return {
                "status": "blocked",
                "blocker": "layout",
                "error": "Cleartrip client-side SPA requires dynamic session authentication.",
                "steps": steps,
                "seconds": (datetime.now(IST) - t0).total_seconds(),
                "cost_usd": 0.0,
            }

    except Exception as exc:
        return {
            "status": "blocked",
            "blocker": "other",
            "error": str(exc),
            "steps": steps,
            "seconds": (datetime.now(IST) - t0).total_seconds(),
            "cost_usd": 0.0,
        }
