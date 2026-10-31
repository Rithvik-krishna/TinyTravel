GOAL = """Open the provided URL. Search for hotels in {city} for {check_in} to {check_out}, {guests} adults, {rooms} room.
Find the hotel named "{hotel_name}" (exact name; if not found, return blocker "other" with notes).
Select the cheapest room that fits {guests} adults. Prefer free cancellation; otherwise cheapest, and report the cancellation policy.
Proceed as a GUEST through checkout using: Name "Test Guest", email "test.guest+probe@example.com", phone "9000000000".
Record the displayed total at each step in price_trail with the currency shown on screen. Do not convert currencies.
Record every fee line, pre-selected add-on, and any urgency/scarcity message.
STOP at the payment page. Never enter payment details, never click pay/confirm/book, never log in, never enter an OTP, never create an account.
If blocked (login, OTP, captcha, empty page), stop and return the blocker.
Use at most 30 steps. Return ONLY JSON in the given schema."""

async def run_checkout(platform: str, hotel_name: str, req: dict):
    raise NotImplementedError("M1: wire TinyFish SDK here (reuse probe.py)")
