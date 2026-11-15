import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import logging
logging.basicConfig(level=logging.INFO)
from api.agents.playbooks.bookingcom import run_bookingcom_playbook

async def main():
    res = await run_bookingcom_playbook(
        "Radisson Blu Atria Bengaluru",
        {"check_in": "2026-11-20", "check_out": "2026-11-21", "guests": 2},
        headless=False,
    )
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
