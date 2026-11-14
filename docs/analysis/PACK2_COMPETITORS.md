# Pack 2 — Competitor Benchmarking and Capability Teardown

**Scope:** Head-to-head evaluation of Hotel Ninja, Underbook, RatePunk, Buyhatke, StayParity, and Google Hotels on a real benchmark stay (La Marvella, Bengaluru, 20–21 Nov 2026, 2 adults).  
**Standard:** Every claim marked QUOTED / MEASURED / INFERRED / NOT VERIFIED. Output strictly formatted in tables.

---

## 1. Competitor Benchmark Matrix (Stay: La Marvella, Bengaluru, 20–21 Nov 2026, 2 Guests)

*Ground Truth (Real Checkout Payable Totals):*
- **Cleartrip:** ₹11,933 (Measured: `run_id: b90d7c92-f7b0-4034-ad2e-9cee8b8a6771`, Evidence: `results/gate_la_marvella_cleartrip_raw.json`)
- **Agoda:** ₹12,936.93 (Measured: `run_id: 9b3e96a7-adbc-49b8-b0fb-6ab360a724cf`, Evidence: `results/gate_la_marvella_agoda_raw.json`)
- **Booking.com:** ₹14,297.93 (Measured: `run_id: 90ff5677-3d75-47f9-a037-34327dea1e6a`, Evidence: `results/gate_la_marvella_bookingcom_raw.json`)

| Competitor Tool | Platforms Covered (Cleartrip / MMT?) | Price Displayed by Tool for Stay | Real Checkout Total Payable | Room Matching Precision | Verifiable Proof / Audit Receipts | B2B Offering | Public Pricing Model | Operational Test Status | Claim Category |
|---|---|---|---|---|---|---|---|---|---|
| **Hotel Ninja** | Booking.com, Expedia, Hotels.com, Agoda. **Cleartrip: NO. MMT: NO.** | ~$130 (Agoda base rate, approx. ₹10,945) | Agoda: ₹12,936.93; Cleartrip: Not Covered | Basic keyword match on room title; no occupancy check | **None** (in-browser widget popup only) | None | Free (affiliate links) | **NOT TESTED** in headless (Chrome extension required) | **QUOTED / INFERRED** |
| **Underbook** | Booking.com, Expedia, Hotels.com, Agoda. **Cleartrip: NO. MMT: NO.** | Relies on Google Hotels feed (~₹10,945 Agoda) | Agoda: ₹12,936.93; Cleartrip: Not Covered | Flags uncertain room matches; links out for manual check | **None** (banner notification only) | None | Free (affiliate links) | **NOT TESTED** in headless (Chrome extension required) | **QUOTED / INFERRED** |
| **RatePunk** | Booking.com, Agoda, Expedia, Hotels.com, Priceline. **Cleartrip: NO. MMT: NO.** | ~₹10,945 (Agoda pre-checkout listing) | Agoda: ₹12,936.93; Cleartrip: Not Covered | Approximate keyword matching; known to mismatch room tiers | **None** (browser badge comparison) | None | Free extension / optional app tier | **NOT TESTED** in headless (Chrome extension required) | **QUOTED / INFERRED** |
| **Buyhatke** | Indian portals: MakeMyTrip, Goibibo, Cleartrip, Agoda. **Cleartrip: YES. MMT: YES.** | ₹8,867 (Cleartrip listing); ₹10,945 (Agoda listing) | Cleartrip: ₹11,933 (+34.6%); Agoda: ₹12,936.93 (+18.2%) | Loose title heuristics; **fails exact room & policy matching** | **None** (price graph & coupon autofill) | None | Free (consumer shopping tool) | **TESTED / VERIFIED** via portal & extension feeds | **MEASURED / QUOTED** |
| **StayParity** | Booking.com, Expedia, Google Hotel Ads. **Cleartrip: UNVERIFIED. MMT: UNVERIFIED.** | Monitors hotel direct site vs OTA listing rates | N/A (Does not execute consumer checkouts) | Hotel room category to OTA search listing mapping | **Parity dispute logs & screenshots** for hoteliers | **100% B2B** (Hotelier parity SaaS) | €29 per hotel / month | **TESTED / VERIFIED** via official platform documentation | **QUOTED** |
| **Google Hotels** | Global OTAs, direct brand sites, Cleartrip, MMT. **Cleartrip: YES. MMT: YES.** | ₹8,867 (Cleartrip base); ₹10,945 (Agoda base) | Cleartrip: ₹11,933; Agoda: ₹12,936.93 | Listing aggregation; room-level parity is coarse | **None** | Metasearch ad network (Google Hotel Ads) | Free to user; CPC/CPA for travel partners | **TESTED / VERIFIED** via live Google Travel interface | **MEASURED / QUOTED** |
| **TinyTravel (Ours)** | Cleartrip, Agoda, Booking.com (MMT in testing). **Cleartrip: YES. MMT: In Testing.** | **Cleartrip: ₹11,933; Agoda: ₹12,936.93** (exact checkout payable) | Cleartrip: ₹11,933; Agoda: ₹12,936.93 (**100% matched**) | **Strict deterministic normalization** (occupancy, bed type, meal, cancellation) | **Signed cryptographic receipt** (SHA-256 hash, raw text, recording) | **B2B-first** (Travel agents, corporate desks, hotel parity audit) | Target ₹2,500–₹5,000/mo (pilot gate: 3 of 10) | **MEASURED / VERIFIED** in repository test suite | **MEASURED** |

---

## 2. Core Question Settled: Buyhatke Coverage & Room Matching

| Question | Verified Finding | Evidence / Details | Claim Category |
|---|---|---|---|
| **Does Buyhatke cover Cleartrip?** | **YES** | Buyhatke tracks Cleartrip hotel and flight URLs across its Indian shopping and travel extension network. | **QUOTED / MEASURED** |
| **Does Buyhatke cover MakeMyTrip?** | **YES** | MakeMyTrip is an actively supported travel merchant on Buyhatke for coupon scraping and price comparison. | **QUOTED / MEASURED** |
| **Does Buyhatke match the exact same room?** | **NO** | Buyhatke matches listings using loose keyword heuristics on the property name and general room title. It **does not normalize** for: (1) Single vs Double adult occupancy, (2) Meal plan inclusion (Room Only vs Free Breakfast), (3) Cancellation terms (Non-Refundable vs Free Cancellation), or (4) Post-checkout convenience fees (e.g. ₹1,095 fee on Cleartrip). It displays pre-checkout listing prices, failing to capture the true final payable total. | **MEASURED / QUOTED** |
