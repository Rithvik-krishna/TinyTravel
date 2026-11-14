# TinyTravel — Startup Pitch Deck Outline (8–10 Slides)

**Target Event:** Startup Buildathon India 2026 (Google AI / Google Cloud)  
**Standard:** Real data only, quoted competitor facts (<15 words + URL), B2B marked as hypothesis, zero unverified numbers.

---

### Slide 1: Title & Tagline
- **Headline:** TinyTravel
- **Tagline:** The price you see isn't the price you pay.
- **Sub-headline:** The autonomous, verified all-in price layer for hotel booking.
- **Presenter Team:** Nikhil Srinivas, Rithvik Krishna, Harsh Chaturvedi, Raghav Duggal.
- **Bottom Callout:** Built with Google Gemini & Google Cloud.

---

### Slide 2: The Problem — The Checkout Trap
- **The Consumer Reality:** Travellers search for hotels on MakeMyTrip, Agoda, and Cleartrip. The listed price looks attractive, but after clicking through 5 checkout pages, entering guest details, and reaching payment, the price jumps.
- **The Core Flaw:** Listing scrapers and meta-search engines (Google Hotels, Trivago) only display listing/API rates. They miss mandatory convenience fees, dynamic surge add-ons, and payment surcharges that only exist on the final payment screen.
- **The Time Sink:** Users waste 15–30 minutes opening 5+ browser tabs to discover who actually has the lowest payable price for the exact same room.

---

### Slide 3: Real Evidence — n=1 Measured Case Study
- **Headline:** Observed On A Live Checkout Run: +34.6% Fee Leak
- **Verified Benchmark Run:**
  - **Hotel:** La Marvella, Bengaluru (Stay: 20–21 Nov 2026, 2 Adults, 1 Room).
  - **Platform:** Cleartrip.
  - **Audit Run ID:** `b90d7c92-f7b0-4034-ad2e-9cee8b8a6771` (Evidence File: `results/gate_la_marvella_cleartrip_raw.json`).
  - **Search Listing Price:** ₹8,867
  - **Final Payment Page Payable:** ₹11,933 (**+34.6% increase**, +₹3,066 jump).
- **Exact Reconciled Breakdown:**
  - Base Room: ₹15,639
  - Hotel Taxes: +₹1,971
  - Property Discount: −₹4,692
  - Coupon Code (CTHOTEL): −₹2,080
  - Convenience Fee: +₹1,095
  - **Final Payable Total:** **₹11,933** (100% reconciled to the rupee).
- **Key Takeaway:** You cannot know the true cheapest platform without executing checkout.

---

### Slide 4: The Solution — TinyTravel Autonomous Verification
- **What We Built:** Autonomous AI agents that walk hotel checkouts as guests, stop before payment, extract true payable sums, and attach signed cryptographic receipts.
- **Core Loop:**
  1. **Intake:** Natural language query parsed instantly by Google Gemini 2.5 Flash.
  2. **Verify:** Headless browser agent navigates to the payment screen as a dummy guest.
  3. **Reconcile:** Itemized fee lines extracted by Gemini Multimodal and checked for mathematical integrity.
  4. **Compare:** Like-for-like normalization (matching room tiers, meal plans, cancellation policies).
  5. **Handoff:** User receives a pre-verified selection card and direct deep-link to complete booking.

---

### Slide 5: The Competitive Landscape (Quoted Facts Only)
Every claim below is quoted directly from the competitor's primary page (<15 words):

| Competitor | Official Claim / Product Focus | Real Limitations |
|---|---|---|
| **Hotel Ninja** | *"automatically compares hotel prices across major booking platforms like Booking.com, Expedia, Hotels.com, and Agoda"* ([Source](https://hotel-ninja.com)) | Listing scraper / popup estimate. **Cleartrip: NO. MakeMyTrip: NO.** No guest checkout execution. |
| **Underbook** | *"Automatically checks dozens of sites for lower hotel prices, including taxes and fees"* ([Source](https://underbook.co)) | Uses Google Hotels data feeds. **Cleartrip: NO. MakeMyTrip: NO.** No proof receipts. |
| **RatePunk** | *"automatically compares hotel prices across major booking platforms in real time"* ([Source](https://ratepunk.com)) | Real-time scraper of search APIs; misses checkout-step convenience fees. **Cleartrip: NO. MakeMyTrip: NO.** |
| **Buyhatke** | *"Hotel Compare tool that pulls quotes from various booking websites for the exact same room"* ([Source](https://buyhatke.com)) | Covers Indian portals (Cleartrip/MMT: YES), but relies on search pages & auto-coupons without full checkout walk. |
| **Google Hotels** | *"nightly price with fees or the stay total price including taxes and fees"* ([Source](https://google.com/travel/hotels)) | Dependent on partner self-reported feeds. No independent verification or proof receipts. |
| **TinyTravel** | *"The verified all-in price layer for hotel booking: real payable price with proof"* | **Autonomous guest checkout walks.** Captures hidden convenience fees with signed SHA-256 receipts. |

---

### Slide 6: System Architecture & Google AI Integration
- **Client & Interaction:** Next.js web application and interactive in-page extension prototype.
- **Google Gemini Core:**
  - **Gemini 2.5 Flash:** Instant structured parsing of natural language travel requirements.
  - **Gemini 2.5 Pro Multimodal:** Visual and DOM extraction of complex checkout fee breakdowns and coupon rules.
- **Scalable Cloud Infrastructure (Google Cloud):**
  - **Google Cloud Run:** Serverless deployment of FastAPI orchestration and Playwright verification workers.
  - **Google Cloud SQL (PostgreSQL):** Time-stamped price database with automated freshness TTLs.
  - **Google Cloud Storage:** Signed evidence store (DOM text snapshots, screenshots, receipt hashes).
  - **Google Secret Manager:** Secure credential and API key isolation.

---

### Slide 7: Business Model & Monetization *(Hypothesis, Not Validated)*
*Note: The following business streams represent our target hypothesis and are pending customer discovery validation.*
- **Lead Revenue: B2B Subscriptions (Hypothesis, Not Validated):**
  - **Target Buyers:** Boutique travel agencies, corporate travel desks, hotel revenue managers.
  - **Value Proposition:** Instant audit-ready quotes across OTAs, elimination of manual checkout checking, and signed rate parity dispute evidence.
  - **Target Pricing Hypothesis:** ₹2,500 – ₹5,000/month per agency seat.
- **Consumer Funnel: Affiliate & Handoff:**
  - Free consumer comparison tool acts as the organic top-of-funnel acquisition channel, earning standard OTA affiliate commissions upon verified handoff.
- **Future Data Assets:** Aggregated fee transparency and pricing volatility data sold to industry analysts and consumer protection compliance teams.

---

### Slide 8: The Moat — Freshness, Accuracy & Re-Check Agreement
- **The Data Moat:** Every verification is cached with a strict freshness timestamp, transforming slow browser automation into instant database reads for subsequent users.
- **The Moat Metric:** Number of fresh, verified `hotel × platform × stay-date` keys in the database.
- **Quality Safeguard (Re-Check Agreement Rate):**
  - We measure the percentage of live pre-payment re-checks whose final payable price matches the cached price within ±1%.
  - Maintains cryptographic reliability while driving verification costs down from ~$0.40 to near-zero as cache hit rates rise.

---

### Slide 9: Product Roadmap & Execution Status
- **Current State (MVP Built & Reconciled):**
  - End-to-end multi-platform discovery and guest checkout pipeline running on Cleartrip, Agoda, and Booking.com.
  - 100% pure-function scoring engine, room normalization rules, and golden test suite (105 passing tests).
  - Own Agent Playwright spike executed: 0/5 verified (median 7.0s; blocked by Cleartrip dynamic SPA search input), validating multimodal agent necessity.
- **City Buildathon Sprint (20–21 Nov 2026):**
  - Full Google Gemini 2.5 multimodal integration on Google Cloud Run with Secret Manager.
  - Interactive browser extension prototype demonstrating in-page comparison.
- **Post-Buildathon Milestones:**
  - Complete 10 structured B2B customer interviews (Target Gate: 3 of 10 committing to paid pilot).
  - Launch public verified price dataset across top 50 business hotels in Bengaluru and Mumbai.

---

### Slide 10: Summary & The Ask
- **Summary:** TinyTravel solves hotel price deception by walking checkouts autonomously, attaching cryptographic proof, and creating the definitive verified all-in price layer for travel.
- **Why We Win:** First to execute checkout-level verification; defensible data asset; built natively on Google AI and Cloud Run.
- **The Ask:** Selection for Startup Buildathon India 2026 City Buildathon (Bengaluru) to scale our Google AI architecture and launch our first B2B enterprise pilots.
