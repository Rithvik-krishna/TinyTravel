"""TinyTravel System and Platform Configuration.
Defines active platforms, disabled platforms with documented reasons, and run constraints.
"""
import os

# Platforms enabled in the live/discovery path
ACTIVE_PLATFORMS = ["Cleartrip", "Agoda", "Booking.com"]

# Disabled platforms with one-line reasons
DISABLED_PLATFORMS = {
    "MakeMyTrip": "Blocked by anti-bot on lite profile; stealth profile retest unconfirmed.",
    "Goibibo": "Blocked by anti-bot on lite profile; stealth profile retest unconfirmed.",
    "EaseMyTrip": "Direct search query parameters unconfirmed; date-picker interaction exceeded timeout.",
}

# Investigation configuration
PROBE_MISSING = os.getenv("PROBE_MISSING", "0") == "1"
MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "3"))
MAX_SPEND_USD = float(os.getenv("MAX_SPEND_USD", "4.0"))
AGENT_TIMEOUT_S = int(os.getenv("AGENT_TIMEOUT_S", "360"))
INTAKE_MODEL = os.getenv("INTAKE_MODEL", "claude-3-5-sonnet-20241022")
