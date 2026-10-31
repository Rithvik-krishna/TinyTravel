# TinyTravel v0 Feature Freeze

**Date:** 2026-10-31  
**Status:** Frozen (`v0-freeze`)  
**Scope:** P0/P1 Backend Pipeline, Real Replay Fixtures, and Contract Endpoints.

---

## 1. What Is In (Frozen Features)

### A. Core Architecture & Endpoints
- **Intake Service (`POST /api/search`):**
  - Accepts natural language text (e.g. `"Bengaluru, 20-21 Nov 2026, 2 people, breakfast, free cancellation, under 12k"`) or flat-structured search fields.
  - LLM extraction via Claude 3.5 Sonnet (`anthropic`) with a deterministic, offline regex fallback.
- **Event Streaming (`GET /api/search/{id}/stream`):**
  - Real-time Server-Sent Events (SSE) stream (`parsed`, `discovery_started`, `listings_found`, `hotels_grouped`, `agent_started`, `agent_progress`, `agent_done`, `ranking_ready`, `error`).
  - Supports `speed` parameter for playback acceleration.
- **Results (`GET /api/search/{id}/results`):**
  - Strict contract `ResultsResponse` output adhering to `fixtures/demo_run.json`.
  - Incremental polling support (`complete: false` partials -> `complete: true`).
- **Summary Strip:**
  - Real-time summary strip with `listings_found`, `unique_hotels`, `verified`, `unverified`, `blocked`, `avg_fee_leak_pct`.
- **Handoff (`GET /api/offers/{id}/handoff`):**
  - Platform deeplink, step-by-step checklist, copy-paste guest details, and room instructions.
- **Recheck (`POST /api/offers/{id}/recheck`):**
  - Fast single-offer price re-verification with price delta and stability messaging.
- **Price History (`GET /api/history`):**
  - Returns factual recorded historical price points (`captured_at`, `amount`, `currency`, `offer_id`, `run_id`). No synthetic or interpolated records.
- **Fee Intelligence:**
  - Fee kinds categorized (`convenience`, `resort`, `cleaning`, `service`, `tax`, `other`).
  - Fee glossary (`GET /api/fees/glossary`) with clear plain-language descriptions.
- **Evidence & Reporting:**
  - Self-contained printable HTML evidence report (`GET /api/search/{id}/report`).
  - Polite, factual draft fee message for platforms (`GET /api/offers/{id}/report-fee-draft`).
  - Static evidence serving under `/evidence/{filename}` with fallback to `fixtures/evidence/`.

### B. Operating Modes (`DATA_MODE`)
- **`mock`:** Instant responses matching `fixtures/demo_run.json` and `fixtures/sse_script.json`. Zero external dependencies.
- **`fake`:** Full local execution of the pipeline using canned agent steps and deterministic deduplication. Zero credit spend.
- **`saved`:** Exact replay of a full real investigation (`fixtures/saved_run.json`) and SSE timeline (`fixtures/saved_sse_script.json`), with evidence artifacts hosted from `fixtures/evidence/`. Marked `saved=true`, `mock=false`.
- **`live`:** Full autonomous browser investigation across active OTAs using TinyFish Web Agent API.
  - Concurrency limited via semaphore (`MAX_CONCURRENT_RUNS`).
  - Invariant safety enforcement: Dummy guest details only, STOP at payment page, zero fabricated prices.

### C. Active Platforms
- **Cleartrip:** Full discovery and checkout probe verified end-to-end.
- **Agoda:** Currency locked to INR, search and room selection verified.
- **Booking.com:** Room occupancy matching guests requirement verified.

---

## 2. What Is Out (Deferred Beyond v0)

1. **MakeMyTrip / Goibibo / EaseMyTrip:**
   - Disabled due to aggressive bot detection / login wall barriers observed in early probes.
2. **Payment Execution / Booking Completion:**
   - Probes strictly stop at the payment page. Actual payment processing, card tokenization, and OTP entry are explicitly forbidden by safety invariants.
3. **User Authentication & Accounts:**
   - All runs operate as guest probes with dummy data. No user auth, session persistence across users, or user profiles in v0.
4. **Dynamic Price Negotiation / Automated Discount Hunting:**
   - Price observation and fee breakdown only; no automated promo coupon brute-forcing or booking bidding in v0.
5. **Mobile Native App:**
   - Web frontend and REST/SSE API contract only.

---

## 3. Verification & Compliance
- Full pytest test suite passing (84+ tests).
- All fixtures validate against strict Pydantic v2 contract schemas (`ResultsResponse`, `ScriptFile`).
