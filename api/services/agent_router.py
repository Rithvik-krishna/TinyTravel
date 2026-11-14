"""
Agent Router: Hybrid Execution Strategy with TinyFish Fallback.
Routes checkout verification requests to the local Playwright playbook first (for Cleartrip spike).
If blocked, missing dependencies, or unverified, falls back to TinyFish.
"""
import logging
from typing import Dict, Any, Optional

from .tinyfish import run_agent, AgentRun

logger = logging.getLogger("tinytravel.router")


async def run_hybrid_agent(
    platform: str,
    hotel_name: str,
    req: dict,
    *,
    use_spike: bool = True,
    profile: str = "lite",
    timeout_s: float = 360.0,
) -> Dict[str, Any]:
    """
    Route checkout verification to Playwright playbook (Cleartrip spike),
    falling back cleanly to TinyFish on failure or block.
    """
    if platform.lower() == "cleartrip" and use_spike:
        try:
            from scripts.playwright_cleartrip import run_cleartrip_playbook
            logger.info(f"Attempting Cleartrip Playwright playbook spike for '{hotel_name}'...")
            res = await run_cleartrip_playbook(hotel_name, req, timeout_s=min(timeout_s, 120.0))
            if res.get("status") == "verified":
                logger.info("Playwright playbook spike succeeded.")
                return res
            logger.warning(
                f"Playwright spike failed/blocked ({res.get('blocker')}: {res.get('error')}). "
                "Falling back to TinyFish runner."
            )
        except Exception as e:
            logger.warning(f"Playwright spike crashed ({e}). Falling back to TinyFish runner.")

    # Fallback to TinyFish
    from agents.checkout import verify_offer
    return await verify_offer(platform, hotel_name, req, profile=profile)
