# TinyTravel — Phased Build Plan + Mock Demo Data

**Event:** Swim with TinyFish, Bangalore, 31 Oct 2026, 11:00–17:00, 4 people.
**Scope:** unchanged from `TinyTravel_Build_Plan.md` (all P0, P1, P2 kept). This file only adds **phases** and **preloaded frontend data**. Contracts in section 5 of the original stay the source of truth, plus the additions below.

Owners: **M1** agents · **M2** backend/intelligence · **M3** frontend · **M4** integration/pitch.

---

## 1. Phases at a glance

| Phase | Time | Goal | Exit gate |
|---|---|---|---|
| 0 | 11:00–11:30 | Scope lock, contracts frozen, fixtures in repo | Fixtures committed, `DATA_MODE=mock` works |
| 1 | 11:30–13:00 | Parallel foundations (UI on mock, agents, logic, API) | Each owner's module passes on fixture data |
| 2 | 13:00–14:00 | One hotel verified end to end, live | **14:00 GATE** |
| 3 | 14:00–15:00 | Finish P0: 3 platforms × 3 hotels, verdict, handoff, evidence | All P0 live, blocked states honest |
| 4 | 15:00–15:45 | P1 features, P2 in parallel by whoever is free | P1 working on live data |
| 5 | 15:45–16:00 | **Feature freeze**, record fixture run | Saved run labelled |
| 6 | 16:00–16:40 | Test 10+ queries, fix, mobile check | Demo query stable |
| 7 | 16:40–17:00 | Rehearse pitch twice, final deploy | `demo` branch tagged |

Note: the original had freeze at both 15:45 and 16:00. This plan uses **15:45**.

---

## 2. Phase detail

### Phase 0 — Kickoff (11:00–11:30)
- **All:** read the official problem statement, map it to features, lock scope (fallbacks: procurement BOM→cart, rental truth, injection range).
- **M4:** create repo from the layout in the original (section 10), commit `fixtures/demo_run.json` and `fixtures/sse_script.json` (Appendices A and B), freeze contracts by 11:30 including the **contract additions** in section 4.
- **M3:** drop placeholder assets in `web/public/mock/` (section 3.4), set `NEXT_PUBLIC_DATA_MODE=mock`.
- **M1:** run MMT and Goibibo `stealth` retests in the background; ask organisers about `max_steps` beta, concurrency limit, screenshot capture, human takeover, judging criteria.
- **Decide now:** evidence = recording link + `page_text` of payment page + extracted values + timestamp, until real screenshots are confirmed.

### Phase 1 — Parallel foundations (11:30–13:00)
| Owner | Build | Test against |
|---|---|---|
| **M3** | Search screen (sentence → editable chips), Investigation screen (live tiles, status, counters), Hotel comparison, Price evidence modal, Verdict shell, mobile-first layout | Mock data only (labelled MOCK) |
| **M1** | Discovery + checkout agents, strict ProbeResult JSON, `streaming_url`, client timeout ~6 min, prompt step cap **30** (Agoda and Booking used 23), exact-hotel-name targeting | Real runs; save raw outputs to `fixtures/real/` |
| **M2** | `dedupe.py` (rapidfuzz, 0.90/0.75 thresholds), `normalize.py` (hard filters), `scoring.py` (fee leak, transparency, ranking), `handoff.py` | **`demo_run.json` as golden test**: functions must reproduce its `groups`, `fee_leak_pct`, `transparency`, `ranking`, `verdicts` |
| **M4** | FastAPI skeleton, DB, SSE endpoint (mock mode replays `sse_script.json`), evidence storage, `.env` hygiene | Mock SSE end to end into M3's tiles |

### Phase 2 — Vertical slice (13:00–14:00)
Wire **one hotel, live**: discovery → match → checkout → evidence → price → UI.
Swap mock to live **one endpoint at a time** (table in 3.3). Keep mock mode working as fallback.
**14:00 GATE:** one real hotel verified end to end. If missed, stop P1 and fix.

### Phase 3 — Finish P0 (14:00–15:00)
- Run 3 platforms in parallel, 3 target hotels (check concurrency limit first).
- Verdict cards: cheapest verified, safe-cheapest, best for you.
- Handoff Pack: deep link, QR, selection card, copy-paste details.
- Evidence modal on real data. Blocked / unverified tiles visible, never scored.
- Verification rule enforced server-side (reached payment + payable + evidence + reconcile ±1%).

### Phase 4 — P1, with P2 in parallel (15:00–15:45)
- **P1:** onboarding (5 chip steps + Skip + deal mode), Fee Leak % + pressure badges, transparency score with breakdown, Re-check button, dashboard summary strip.
- **P2 (anyone free):** evidence PDF / shareable report + "report this fee" draft, fee tooltips (GST, convenience, resort), price history across runs.
- Show **taxes separately from fees** in the fee explainer, so GST is not called a hidden fee.
- Cut order if behind: dashboard stats → transparency breakdown → onboarding steps 3–5 → re-check → tooltips/PDF. **Never cut** end-to-end verification, evidence, honest blocked states, Handoff Pack.

### Phase 5 — Freeze + fixture (15:45–16:00)
- No new features. Record one full real investigation as `fixtures/saved_run.json`, labelled with its capture time.
- Budget: max 2 full investigations before the pitch (~$3.8 each).

### Phase 6 — Hardening (16:00–16:40)
- 10+ query tests, pick the stable demo query, fix failures, no retry loops.
- Mobile check, dark/light check, QR scan from a phone.
- **Pitch timing fix:** a live run takes 153–297 s but the live beat is 75 s. Start the 1-hotel × 3-platform run **before** the pitch begins, narrate while tiles run, and cut to the labelled saved run for the full comparison.
- Closing line: replace "You pay in one tap" with "You pay on the real site, we never see your password" (deep links may not restore the cart).

### Phase 7 — Rehearse (16:40–17:00)
- 3-minute pitch twice, Q&A answers from the original (section 16), final deploy, `demo` branch tagged.

---

## 3. Frontend mock layer

### 3.1 Rules
1. `NEXT_PUBLIC_DATA_MODE=mock|live`. Default `mock` until Phase 2.
2. Every mock object has `"mock": true`. The UI shows a **MOCK DATA** badge whenever any rendered object has it. Never present mock as live.
3. Only `h1_cleartrip` uses real probe numbers (₹8,210 → ₹11,276, +37.3%). All other numbers, ratings and hotel names are invented to exercise UI states.
4. Fee line labels on the Cleartrip offer are placeholders; only the amounts are real.

### 3.2 Adapter (one file, one swap point)
```ts
// web/lib/dataSource.ts
import demo from "@/fixtures/demo_run.json";
import script from "@/fixtures/sse_script.json";

const MOCK = process.env.NEXT_PUBLIC_DATA_MODE !== "live";

export async function startSearch(text: string) {
  return MOCK ? { search_id: "mock_search" } : (await fetch("/api/search", { method: "POST", body: JSON.stringify({ text }) })).json();
}
export async function getResults(id: string) {
  return MOCK ? demo : (await fetch(`/api/search/${id}/results`)).json();
}
export async function getHandoff(offerId: string) {
  return MOCK ? demo.handoff : (await fetch(`/api/offers/${offerId}/handoff`)).json();
}
export async function recheck(offerId: string) {
  return MOCK ? demo.rechecks[0] : (await fetch(`/api/offers/${offerId}/recheck`, { method: "POST" })).json();
}

// Replays sse_script.json with the same event names as the live SSE stream.
export function openStream(id: string, onEvent: (e: string, d: any) => void, speed = 1) {
  if (!MOCK) {
    const es = new EventSource(`/api/search/${id}/stream`);
    ["parsed","discovery_started","listings_found","hotels_grouped","agent_started",
     "agent_progress","agent_done","ranking_ready","error"].forEach(t =>
      es.addEventListener(t, (m: MessageEvent) => onEvent(t, JSON.parse(m.data))));
    return () => es.close();
  }
  const timers = script.events.map(ev => setTimeout(() => onEvent(ev.event, ev.data), ev.t_ms / speed));
  return () => timers.forEach(clearTimeout);
}
```

### 3.3 Mock to live swap order
| Phase 2 order | Mock source | Live endpoint |
|---|---|---|
| 1 | `sse_script.json` | `GET /api/search/:id/stream` |
| 2 | `offers[]` | `GET /api/search/:id/results` |
| 3 | `handoff` | `GET /api/offers/:id/handoff` |
| 4 | `rechecks[0]` | `POST /api/offers/:id/recheck` |

### 3.4 Placeholder assets (`web/public/mock/`)
- `evidence-placeholder.svg`: grey card reading "MOCK SCREENSHOT".
- `tile-cleartrip.html`, `tile-agoda.html`, `tile-booking.html`: static fake browser frame with a CSS progress animation, labelled MOCK. Rendered in the same iframe slot as the real `streaming_url`.

### 3.5 Which fixture exercises which UI state
| UI state | Fixture |
|---|---|
| High fee leak (37.3%) | `h1_cleartrip` |
| Pressure messages badge | `h1_agoda`, `h1_booking`, `h2_agoda` |
| Pre-ticked add-on warning | `h2_cleartrip` |
| Non-comparable warning (non-refundable) | `h1_booking` |
| Cheapest verified ≠ safe-cheapest | hotel `h1` (Booking vs Agoda) |
| Best-for-you ≠ cheapest (lower leak wins) | hotel `h2` (Agoda over Cleartrip) |
| Blocked tile (captcha), no score | `h2_booking` |
| Unverified tile (timeout), no score | `h3_booking` |
| "Possible match", not merged | group `h3` (confidence 0.82) |
| Re-check drift ₹10,412 → ₹10,690 | `rechecks[0]` on `h1_agoda` |
| Transparency with stability included | `h1_agoda` (others show re-normalised, N/A stability) |
| Summary strip counters | `summary_strip` |
| Handoff Pack + QR + selection card | `handoff` (`h1_agoda`) |
| Onboarding result | `travel_profile` |
| Search chips | `search_request` |

Hero story for the pitch: **La Marvella (`h1`)**. Cleartrip shows the cheapest listing (₹8,210) but charges the most (₹11,276). Agoda is ₹10,412 with free cancellation. Booking is cheapest overall (₹9,821) but non-refundable.

---

## 4. Contract additions (freeze at 11:30)

Added to the original section 5 contracts, all already present in the mock data:

| Where | Field | Meaning |
|---|---|---|
| every object | `mock: bool` | Drives the MOCK DATA badge |
| Offer | `offer_id`, `hotel_id` | Join keys |
| Offer | `cancellation_category` | `free | partial | non_refundable` (normalization key) |
| Offer | `reconciliation` | `ok | mismatch | null` |
| Offer | `fee_leak_pct` | Observed on this run, `null` if unverified |
| Offer | `transparency` | `{score, breakdown, note}`, score `null` if not verified |
| Offer | `blocker` | `captcha | login | otp | timeout | other | null` |
| Group | `match_status`, `confidence`, `why` | `merged | suggested`, shown in UI |
| Verdicts | `overall` + `per_hotel{}` | Three outputs per hotel and across all hotels |
| Recheck | `previous`, `current`, `delta`, `delta_pct`, `trail_diff` | Real drift display |

**Assumptions made in the mock scoring (confirm or change):**
- Price stability points: 20 × (1 − % change / 10), zero at ≥10% change.
- Ranking price score: 100 × lowest payable / this payable, across verified offers.
- Prefs match: share of {breakfast, free cancellation} satisfied.
- Quality: rating / 5 × 100. Ranking weights are the original "Best value" row.
- Verdicts are computed per hotel, plus one overall set.

---

## 5. Definition of done per phase

- [ ] **P0:** fixtures in repo, mock mode renders every state in 3.5
- [ ] **P1:** each module passes on `demo_run.json` as golden test
- [ ] **P2:** one real hotel verified end to end (14:00)
- [ ] **P3:** 3 platforms live, handoff + QR works on a phone, blocked states honest
- [ ] **P4:** onboarding, fee leak, transparency, re-check, strip live; P2 items if time
- [ ] **P5:** feature freeze, saved run recorded and labelled
- [ ] **P6:** demo query stable on 10+ attempts, pitch timing fixed
- [ ] **P7:** pitch rehearsed twice, `demo` branch tagged

---

## Appendix A — `fixtures/demo_run.json`

```json
{
 "_meta": {
  "mock": true,
  "label": "MOCK DATA - not a real run",
  "saved_run_label": "Saved run (mock), 30 Oct 10:08 PM",
  "note": "Only h1_cleartrip uses real probe numbers. Everything else is invented to exercise every UI state."
 },
 "search_request": {
  "destination": "Bengaluru",
  "area_hint": "HSR Layout / Koramangala",
  "check_in": "2026-11-20",
  "check_out": "2026-11-21",
  "guests": 2,
  "rooms": 1,
  "budget_per_night": 12000,
  "must_have": {
   "breakfast": true,
   "free_cancellation": true,
   "parking": false,
   "wifi": true
  },
  "deal_mode": "best_value",
  "currency": "INR",
  "mock": true,
  "raw_text": "Bengaluru, 20-21 Nov, 2 people, breakfast, free cancellation, under 12k"
 },
 "travel_profile": {
  "traveller_type": "family",
  "budget_min": 3000,
  "budget_max": 12000,
  "hotel_type": "any",
  "min_rating": 3.8,
  "must_have": [
   "breakfast",
   "wifi"
  ],
  "prefers_refundable": true,
  "deal_mode": "best_value"
 },
 "hotels": [
  {
   "hotel_id": "h1",
   "canonical_name": "La Marvella",
   "area": "HSR Layout",
   "rating": 4.2
  },
  {
   "hotel_id": "h2",
   "canonical_name": "Lemon Leaf Suites",
   "area": "Koramangala",
   "rating": 4.0
  },
  {
   "hotel_id": "h3",
   "canonical_name": "Urban Nest Inn",
   "area": "HSR Layout",
   "rating": 3.9
  }
 ],
 "listings": [
  {
   "listing_id": "cleartrip_001",
   "platform": "Cleartrip",
   "hotel_name": "La Marvella",
   "address": null,
   "area": "HSR Layout",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.2,
   "shown_price": 8210,
   "currency": "INR",
   "source_url": "https://www.cleartrip.com/hotels/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "agoda_002",
   "platform": "Agoda",
   "hotel_name": "La Marvella",
   "address": null,
   "area": "HSR Layout",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.2,
   "shown_price": 8950,
   "currency": "INR",
   "source_url": "https://www.agoda.com/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "booking_003",
   "platform": "Booking.com",
   "hotel_name": "La Marvella",
   "address": null,
   "area": "HSR Layout",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.2,
   "shown_price": 8700,
   "currency": "INR",
   "source_url": "https://www.booking.com/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "cleartrip_004",
   "platform": "Cleartrip",
   "hotel_name": "Lemon Leaf Suites",
   "address": null,
   "area": "Koramangala",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.0,
   "shown_price": 6400,
   "currency": "INR",
   "source_url": "https://www.cleartrip.com/hotels/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "agoda_005",
   "platform": "Agoda",
   "hotel_name": "Lemon Leaf Suites",
   "address": null,
   "area": "Koramangala",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.0,
   "shown_price": 6900,
   "currency": "INR",
   "source_url": "https://www.agoda.com/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "booking_006",
   "platform": "Booking.com",
   "hotel_name": "Lemon Leaf Suites",
   "address": null,
   "area": "Koramangala",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 4.0,
   "shown_price": 6750,
   "currency": "INR",
   "source_url": "https://www.booking.com/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "cleartrip_007",
   "platform": "Cleartrip",
   "hotel_name": "Urban Nest Inn",
   "address": null,
   "area": "HSR Layout",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 3.9,
   "shown_price": 5200,
   "currency": "INR",
   "source_url": "https://www.cleartrip.com/hotels/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  },
  {
   "listing_id": "booking_008",
   "platform": "Booking.com",
   "hotel_name": "Urban Nest Inn & Suites",
   "address": null,
   "area": "HSR Layout",
   "lat": null,
   "lng": null,
   "phone": null,
   "rating": 3.9,
   "shown_price": 5400,
   "currency": "INR",
   "source_url": "https://www.booking.com/?mock=1",
   "captured_at": "2026-10-30T22:05:00+05:30",
   "mock": true
  }
 ],
 "hotel_groups": [
  {
   "hotel_id": "h1",
   "canonical_name": "La Marvella",
   "area": "HSR Layout",
   "match_status": "merged",
   "confidence": 0.96,
   "why": "Name 100%, same area, phone match",
   "offer_ids": [
    "h1_cleartrip",
    "h1_agoda",
    "h1_booking"
   ]
  },
  {
   "hotel_id": "h2",
   "canonical_name": "Lemon Leaf Suites",
   "area": "Koramangala",
   "match_status": "merged",
   "confidence": 0.93,
   "why": "Name 96%, same area",
   "offer_ids": [
    "h2_cleartrip",
    "h2_agoda",
    "h2_booking"
   ]
  },
  {
   "hotel_id": "h3",
   "canonical_name": "Urban Nest Inn",
   "area": "HSR Layout",
   "match_status": "suggested",
   "confidence": 0.82,
   "why": "Name 82% (\"Urban Nest Inn\" vs \"Urban Nest Inn & Suites\"), same area. Possible match: not merged in pricing",
   "offer_ids": [
    "h3_cleartrip",
    "h3_booking"
   ]
  }
 ],
 "offers": [
  {
   "offer_id": "h1_cleartrip",
   "hotel_id": "h1",
   "run_id": "mock_run_h1_cleartrip",
   "streaming_url": "/mock/tile-cleartrip.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:10:33+05:30",
   "steps": 18,
   "cost_usd": 0.29,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "free",
   "site": "Cleartrip",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "La Marvella",
   "hotel_url": "https://www.cleartrip.com/hotels/?mock=1",
   "room_type": "Deluxe Double",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Free cancellation until 18 Nov 2026, 12:00",
   "price_shown_on_listing": 8210,
   "price_shown_on_room_selection": 8210,
   "price_final_payable": 11276,
   "fee_lines": [
    {
     "label": "Room price (base)",
     "amount": 15639
    },
    {
     "label": "Taxes & fees",
     "amount": 1971
    },
    {
     "label": "Discount",
     "amount": -4692
    },
    {
     "label": "Offer / coupon",
     "amount": -2737
    },
    {
     "label": "Convenience fee",
     "amount": 1095
    }
   ],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [],
   "price_trail": [
    {
     "step": "listing",
     "amount": 8210,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 8210,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 10181,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 11276,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Real probe numbers (Cleartrip). Line labels are placeholders.",
   "fee_leak_pct": 37.3,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8210,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8210,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 11276,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 42,
    "breakdown": {
     "fee_leak": 3.4,
     "addons_pressure": 20,
     "price_stability": null,
     "evidence": 10
    },
    "note": "observed on this run; stability N/A, weights re-normalised"
   }
  },
  {
   "offer_id": "h1_agoda",
   "hotel_id": "h1",
   "run_id": "mock_run_h1_agoda",
   "streaming_url": "/mock/tile-agoda.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:12:28+05:30",
   "steps": 23,
   "cost_usd": 0.37,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "free",
   "site": "Agoda",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "La Marvella",
   "hotel_url": "https://www.agoda.com/?mock=1",
   "room_type": "Deluxe Double",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Free cancellation until 18 Nov 2026, 12:00",
   "price_shown_on_listing": 8950,
   "price_shown_on_room_selection": 8950,
   "price_final_payable": 10412,
   "fee_lines": [
    {
     "label": "Room price",
     "amount": 8950
    },
    {
     "label": "Taxes & service fees",
     "amount": 1462
    }
   ],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [
    "Last 3 rooms left at this price",
    "Price may change"
   ],
   "price_trail": [
    {
     "step": "listing",
     "amount": 8950,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 8950,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 10412,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 10412,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock numbers. Pressure messages copied from real probe.",
   "fee_leak_pct": 16.3,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8950,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8950,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 10412,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 64,
    "breakdown": {
     "fee_leak": 29.6,
     "addons_pressure": 10,
     "price_stability": 14.7,
     "evidence": 10
    },
    "note": "observed on this run"
   }
  },
  {
   "offer_id": "h1_booking",
   "hotel_id": "h1",
   "run_id": "mock_run_h1_booking",
   "streaming_url": "/mock/tile-booking.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:12:57+05:30",
   "steps": 23,
   "cost_usd": 0.37,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "non_refundable",
   "site": "Booking.com",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "La Marvella",
   "hotel_url": "https://www.booking.com/?mock=1",
   "room_type": "Deluxe Double Room",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Non-refundable",
   "price_shown_on_listing": 8700,
   "price_shown_on_room_selection": 8700,
   "price_final_payable": 9821,
   "fee_lines": [
    {
     "label": "Room price",
     "amount": 8700
    },
    {
     "label": "Taxes & charges",
     "amount": 1121
    }
   ],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [
    "Only 2 rooms left on our site"
   ],
   "price_trail": [
    {
     "step": "listing",
     "amount": 8700,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 8700,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 9821,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 9821,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock numbers. Non-refundable: not comparable with free-cancellation offers.",
   "fee_leak_pct": 12.9,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8700,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 8700,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 9821,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 74,
    "breakdown": {
     "fee_leak": 33.9,
     "addons_pressure": 15,
     "price_stability": null,
     "evidence": 10
    },
    "note": "observed on this run; stability N/A, weights re-normalised"
   }
  },
  {
   "offer_id": "h2_cleartrip",
   "hotel_id": "h2",
   "run_id": "mock_run_h2_cleartrip",
   "streaming_url": "/mock/tile-cleartrip.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:10:41+05:30",
   "steps": 19,
   "cost_usd": 0.3,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "free",
   "site": "Cleartrip",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "Lemon Leaf Suites",
   "hotel_url": "https://www.cleartrip.com/hotels/?mock=1",
   "room_type": "Superior Room",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Free cancellation until 19 Nov 2026, 18:00",
   "price_shown_on_listing": 6400,
   "price_shown_on_room_selection": 6400,
   "price_final_payable": 7712,
   "fee_lines": [
    {
     "label": "Room price",
     "amount": 6400
    },
    {
     "label": "Taxes & fees",
     "amount": 768
    },
    {
     "label": "Convenience fee",
     "amount": 544
    }
   ],
   "preselected_addons": [
    "Trip protection (pre-ticked)"
   ],
   "urgency_or_scarcity_messages": [],
   "price_trail": [
    {
     "step": "listing",
     "amount": 6400,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 6400,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 7168,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 7712,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock numbers.",
   "fee_leak_pct": 20.5,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 6400,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 6400,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 7712,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 62,
    "breakdown": {
     "fee_leak": 24.4,
     "addons_pressure": 15,
     "price_stability": null,
     "evidence": 10
    },
    "note": "observed on this run; stability N/A, weights re-normalised"
   }
  },
  {
   "offer_id": "h2_agoda",
   "hotel_id": "h2",
   "run_id": "mock_run_h2_agoda",
   "streaming_url": "/mock/tile-agoda.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:12:15+05:30",
   "steps": 22,
   "cost_usd": 0.35,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "free",
   "site": "Agoda",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "Lemon Leaf Suites",
   "hotel_url": "https://www.agoda.com/?mock=1",
   "room_type": "Superior Room",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Free cancellation until 19 Nov 2026, 18:00",
   "price_shown_on_listing": 6900,
   "price_shown_on_room_selection": 6900,
   "price_final_payable": 7728,
   "fee_lines": [
    {
     "label": "Room price",
     "amount": 6900
    },
    {
     "label": "Taxes & service fees",
     "amount": 828
    }
   ],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [
    "Price may change"
   ],
   "price_trail": [
    {
     "step": "listing",
     "amount": 6900,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 6900,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 7728,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 7728,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock numbers.",
   "fee_leak_pct": 12.0,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 6900,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 6900,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 7728,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 75,
    "breakdown": {
     "fee_leak": 35.0,
     "addons_pressure": 15,
     "price_stability": null,
     "evidence": 10
    },
    "note": "observed on this run; stability N/A, weights re-normalised"
   }
  },
  {
   "offer_id": "h2_booking",
   "hotel_id": "h2",
   "run_id": "mock_run_h2_booking",
   "streaming_url": "/mock/tile-booking.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:10:20+05:30",
   "steps": 9,
   "cost_usd": 0.14,
   "status": "blocked",
   "reconciliation": null,
   "cancellation_category": null,
   "site": "Booking.com",
   "reached_payment_page": false,
   "furthest_step": "blocked",
   "blocker": "captcha",
   "hotel_name": "Lemon Leaf Suites",
   "hotel_url": "https://www.booking.com/?mock=1",
   "room_type": "",
   "max_occupancy": null,
   "meal_plan": "",
   "cancellation_policy": "",
   "price_shown_on_listing": 6750,
   "price_shown_on_room_selection": null,
   "price_final_payable": null,
   "fee_lines": [],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [],
   "price_trail": [
    {
     "step": "listing",
     "amount": 6750,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock: blocked at captcha. Shown honestly, never scored.",
   "fee_leak_pct": null,
   "evidence": [],
   "mock": true,
   "transparency": {
    "score": null,
    "breakdown": null,
    "note": "N/A (not verified)"
   }
  },
  {
   "offer_id": "h3_cleartrip",
   "hotel_id": "h3",
   "run_id": "mock_run_h3_cleartrip",
   "streaming_url": "/mock/tile-cleartrip.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:10:28+05:30",
   "steps": 17,
   "cost_usd": 0.27,
   "status": "verified",
   "reconciliation": "ok",
   "cancellation_category": "free",
   "site": "Cleartrip",
   "reached_payment_page": true,
   "furthest_step": "payment",
   "blocker": null,
   "hotel_name": "Urban Nest Inn",
   "hotel_url": "https://www.cleartrip.com/hotels/?mock=1",
   "room_type": "Standard Double",
   "max_occupancy": 2,
   "meal_plan": "Breakfast included",
   "cancellation_policy": "Free cancellation until 19 Nov 2026, 12:00",
   "price_shown_on_listing": 5200,
   "price_shown_on_room_selection": 5200,
   "price_final_payable": 6106,
   "fee_lines": [
    {
     "label": "Room price",
     "amount": 5200
    },
    {
     "label": "Taxes & fees",
     "amount": 624
    },
    {
     "label": "Convenience fee",
     "amount": 282
    }
   ],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [],
   "price_trail": [
    {
     "step": "listing",
     "amount": 5200,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 5200,
     "currency": "INR"
    },
    {
     "step": "traveller_details",
     "amount": 5824,
     "currency": "INR"
    },
    {
     "step": "payment",
     "amount": 6106,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock numbers.",
   "fee_leak_pct": 17.4,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "listing",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 5200,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 5200,
     "currency": "INR",
     "mock": true
    },
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "payment",
     "captured_at": "2026-10-30T22:10:00+05:30",
     "extracted_value": 6106,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": 73,
    "breakdown": {
     "fee_leak": 28.3,
     "addons_pressure": 20,
     "price_stability": null,
     "evidence": 10
    },
    "note": "observed on this run; stability N/A, weights re-normalised"
   }
  },
  {
   "offer_id": "h3_booking",
   "hotel_id": "h3",
   "run_id": "mock_run_h3_booking",
   "streaming_url": "/mock/tile-booking.html",
   "started_at": "2026-10-30T22:08:00+05:30",
   "finished_at": "2026-10-30T22:13:00+05:30",
   "steps": 25,
   "cost_usd": 0.4,
   "status": "unverified",
   "reconciliation": null,
   "cancellation_category": null,
   "site": "Booking.com",
   "reached_payment_page": false,
   "furthest_step": "room",
   "blocker": "timeout",
   "hotel_name": "Urban Nest Inn & Suites",
   "hotel_url": "https://www.booking.com/?mock=1",
   "room_type": "Standard Double Room",
   "max_occupancy": 2,
   "meal_plan": "",
   "cancellation_policy": "",
   "price_shown_on_listing": 5400,
   "price_shown_on_room_selection": 5400,
   "price_final_payable": null,
   "fee_lines": [],
   "preselected_addons": [],
   "urgency_or_scarcity_messages": [],
   "price_trail": [
    {
     "step": "listing",
     "amount": 5400,
     "currency": "INR"
    },
    {
     "step": "room",
     "amount": 5400,
     "currency": "INR"
    }
   ],
   "currency": "INR",
   "notes": "Mock: stopped at room step, no payable price. Possible match only (0.82).",
   "fee_leak_pct": null,
   "evidence": [
    {
     "type": "screenshot",
     "url": "/mock/evidence-placeholder.svg",
     "step": "room",
     "captured_at": "2026-10-30T22:12:00+05:30",
     "extracted_value": 5400,
     "currency": "INR",
     "mock": true
    }
   ],
   "mock": true,
   "transparency": {
    "score": null,
    "breakdown": null,
    "note": "N/A (not verified)"
   }
  }
 ],
 "verdicts": {
  "deal_mode": "best_value",
  "hero_hotel_id": "h1",
  "ranking": [
   {
    "offer_id": "h3_cleartrip",
    "total": 95.1,
    "components": {
     "price": 100.0,
     "prefs": 100.0,
     "cancellation": 100,
     "quality": 78.0,
     "transparency": 73
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   },
   {
    "offer_id": "h2_agoda",
    "total": 88.2,
    "components": {
     "price": 79.0,
     "prefs": 100.0,
     "cancellation": 100,
     "quality": 80.0,
     "transparency": 75
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   },
   {
    "offer_id": "h2_cleartrip",
    "total": 86.9,
    "components": {
     "price": 79.2,
     "prefs": 100.0,
     "cancellation": 100,
     "quality": 80.0,
     "transparency": 62
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   },
   {
    "offer_id": "h1_agoda",
    "total": 80.3,
    "components": {
     "price": 58.6,
     "prefs": 100.0,
     "cancellation": 100,
     "quality": 84.0,
     "transparency": 64
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   },
   {
    "offer_id": "h1_cleartrip",
    "total": 76.6,
    "components": {
     "price": 54.2,
     "prefs": 100.0,
     "cancellation": 100,
     "quality": 84.0,
     "transparency": 42
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   },
   {
    "offer_id": "h1_booking",
    "total": 50.1,
    "components": {
     "price": 62.2,
     "prefs": 50.0,
     "cancellation": 0,
     "quality": 84.0,
     "transparency": 74
    },
    "weights": {
     "price": 35,
     "prefs": 25,
     "cancellation": 20,
     "quality": 10,
     "transparency": 10
    }
   }
  ],
  "overall": {
   "cheapest_verified": "h3_cleartrip",
   "safe_cheapest": "h3_cleartrip",
   "best_for_you": "h3_cleartrip",
   "headlines": {
    "cheapest_verified": "Urban Nest Inn on Cleartrip: you pay INR 6,106, listing showed INR 5,200",
    "safe_cheapest": "Urban Nest Inn on Cleartrip: INR 6,106 with free cancellation",
    "best_for_you": "Urban Nest Inn on Cleartrip: INR 6,106"
   }
  },
  "per_hotel": {
   "h1": {
    "cheapest_verified": "h1_booking",
    "safe_cheapest": "h1_agoda",
    "best_for_you": "h1_agoda",
    "headlines": {
     "cheapest_verified": "La Marvella on Booking.com: you pay INR 9,821, listing showed INR 8,700",
     "safe_cheapest": "La Marvella on Agoda: INR 10,412 with free cancellation",
     "best_for_you": "La Marvella on Agoda: INR 10,412"
    }
   },
   "h2": {
    "cheapest_verified": "h2_cleartrip",
    "safe_cheapest": "h2_cleartrip",
    "best_for_you": "h2_agoda",
    "headlines": {
     "cheapest_verified": "Lemon Leaf Suites on Cleartrip: you pay INR 7,712, listing showed INR 6,400",
     "safe_cheapest": "Lemon Leaf Suites on Cleartrip: INR 7,712 with free cancellation",
     "best_for_you": "Lemon Leaf Suites on Agoda: INR 7,728"
    }
   },
   "h3": {
    "cheapest_verified": "h3_cleartrip",
    "safe_cheapest": "h3_cleartrip",
    "best_for_you": "h3_cleartrip",
    "headlines": {
     "cheapest_verified": "Urban Nest Inn on Cleartrip: you pay INR 6,106, listing showed INR 5,200",
     "safe_cheapest": "Urban Nest Inn on Cleartrip: INR 6,106 with free cancellation",
     "best_for_you": "Urban Nest Inn on Cleartrip: INR 6,106"
    }
   }
  },
  "non_comparable_warnings": [
   {
    "hotel_id": "h1",
    "offer_id": "h1_booking",
    "message": "Booking.com room is non-refundable; not comparable with the free-cancellation rooms on Cleartrip and Agoda."
   }
  ],
  "mock": true
 },
 "handoff": {
  "offer_id": "h1_agoda",
  "platform": "Agoda",
  "deep_link": "https://www.agoda.com/",
  "qr_png_base64": "",
  "qr_note": "Mock: UI renders QR from deep_link client-side (qrcode lib). Backend fills qr_png_base64 in live mode.",
  "selection_card": {
   "hotel": "La Marvella",
   "room_type": "Deluxe Double",
   "meal_plan": "Breakfast included",
   "cancellation": "Free cancellation until 18 Nov 2026, 12:00",
   "dates": "20-21 Nov 2026 (1 night)",
   "guests": 2,
   "expected_final_payable": 10412,
   "currency": "INR",
   "verified_at": "2026-10-30T22:13:00+05:30"
  },
  "copy_paste": {
   "name": "Test Guest",
   "email": "test.guest+probe@example.com",
   "phone": "9000000000"
  },
  "disclaimer": "Price verified at 10:13 PM. Re-check before paying; prices can change.",
  "mock": true
 },
 "rechecks": [
  {
   "recheck_id": "mock_recheck_h1_agoda",
   "offer_id": "h1_agoda",
   "status": "done",
   "previous": {
    "amount": 10412,
    "at": "2026-10-30T22:08:00+05:30"
   },
   "current": {
    "amount": 10690,
    "at": "2026-10-30T22:31:00+05:30"
   },
   "delta": 278,
   "delta_pct": 2.7,
   "elapsed_minutes": 23,
   "trail_diff": [
    {
     "step": "payment",
     "before": 10412,
     "after": 10690
    }
   ],
   "message": "Price moved INR 10,412 -> INR 10,690 in 23 min (observed).",
   "mock": true
  }
 ],
 "summary_strip": {
  "listings_found": 24,
  "unique_hotels": 3,
  "verified": 6,
  "unverified": 1,
  "blocked": 1,
  "avg_fee_leak_pct": 19.4
 }
}
```

## Appendix B — `fixtures/sse_script.json`

Events replay by `t_ms` (total ~26.5 s at speed 1; pass `speed=2` to halve it).

```json
{"mock":true,"speed_default":1.0,"total_ms":26550,"events":[{"t_ms":300,"event":"parsed","data":{"search_request":{"destination":"Bengaluru","area_hint":"HSR Layout / Koramangala","check_in":"2026-11-20","check_out":"2026-11-21","guests":2,"rooms":1,"budget_per_night":12000,"must_have":{"breakfast":true,"free_cancellation":true,"parking":false,"wifi":true},"deal_mode":"best_value","currency":"INR","mock":true,"raw_text":"Bengaluru, 20-21 Nov, 2 people, breakfast, free cancellation, under 12k"}}},{"t_ms":800,"event":"discovery_started","data":{"platforms":["Cleartrip","Agoda","Booking.com"]}},{"t_ms":3300,"event":"listings_found","data":{"count":24,"by_platform":{"Cleartrip":8,"Agoda":8,"Booking.com":8}}},{"t_ms":4100,"event":"hotels_grouped","data":{"hotel_groups":[{"hotel_id":"h1","canonical_name":"La Marvella","area":"HSR Layout","match_status":"merged","confidence":0.96,"why":"Name 100%, same area, phone match","offer_ids":["h1_cleartrip","h1_agoda","h1_booking"]},{"hotel_id":"h2","canonical_name":"Lemon Leaf Suites","area":"Koramangala","match_status":"merged","confidence":0.93,"why":"Name 96%, same area","offer_ids":["h2_cleartrip","h2_agoda","h2_booking"]},{"hotel_id":"h3","canonical_name":"Urban Nest Inn","area":"HSR Layout","match_status":"suggested","confidence":0.82,"why":"Name 82% (\"Urban Nest Inn\" vs \"Urban Nest Inn & Suites\"), same area. Possible match: not merged in pricing","offer_ids":["h3_cleartrip","h3_booking"]}]}},{"t_ms":4500,"event":"agent_started","data":{"run_id":"mock_run_h1_cleartrip","offer_id":"h1_cleartrip","platform":"Cleartrip","hotel":"La Marvella","streaming_url":"/mock/tile-cleartrip.html"}},{"t_ms":4900,"event":"agent_started","data":{"run_id":"mock_run_h1_agoda","offer_id":"h1_agoda","platform":"Agoda","hotel":"La Marvella","streaming_url":"/mock/tile-agoda.html"}},{"t_ms":5300,"event":"agent_started","data":{"run_id":"mock_run_h1_booking","offer_id":"h1_booking","platform":"Booking.com","hotel":"La Marvella","streaming_url":"/mock/tile-booking.html"}},{"t_ms":5700,"event":"agent_started","data":{"run_id":"mock_run_h2_cleartrip","offer_id":"h2_cleartrip","platform":"Cleartrip","hotel":"Lemon Leaf Suites","streaming_url":"/mock/tile-cleartrip.html"}},{"t_ms":6100,"event":"agent_started","data":{"run_id":"mock_run_h2_agoda","offer_id":"h2_agoda","platform":"Agoda","hotel":"Lemon Leaf Suites","streaming_url":"/mock/tile-agoda.html"}},{"t_ms":6500,"event":"agent_started","data":{"run_id":"mock_run_h2_booking","offer_id":"h2_booking","platform":"Booking.com","hotel":"Lemon Leaf Suites","streaming_url":"/mock/tile-booking.html"}},{"t_ms":6900,"event":"agent_started","data":{"run_id":"mock_run_h3_cleartrip","offer_id":"h3_cleartrip","platform":"Cleartrip","hotel":"Urban Nest Inn","streaming_url":"/mock/tile-cleartrip.html"}},{"t_ms":7300,"event":"agent_started","data":{"run_id":"mock_run_h3_booking","offer_id":"h3_booking","platform":"Booking.com","hotel":"Urban Nest Inn & Suites","streaming_url":"/mock/tile-booking.html"}},{"t_ms":7650,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Opening search page"}},{"t_ms":8000,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Opening search page"}},{"t_ms":8350,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Opening search page"}},{"t_ms":8700,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Opening search page"}},{"t_ms":9050,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Opening search page"}},{"t_ms":9400,"event":"agent_progress","data":{"run_id":"mock_run_h2_booking","step_text":"Opening search page"}},{"t_ms":9750,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Opening search page"}},{"t_ms":10100,"event":"agent_progress","data":{"run_id":"mock_run_h3_booking","step_text":"Opening search page"}},{"t_ms":10450,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Searching hotel by name"}},{"t_ms":10800,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Searching hotel by name"}},{"t_ms":11150,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Searching hotel by name"}},{"t_ms":11500,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Searching hotel by name"}},{"t_ms":11850,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Searching hotel by name"}},{"t_ms":12200,"event":"agent_progress","data":{"run_id":"mock_run_h2_booking","step_text":"Searching hotel by name"}},{"t_ms":12550,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Searching hotel by name"}},{"t_ms":12900,"event":"agent_progress","data":{"run_id":"mock_run_h3_booking","step_text":"Searching hotel by name"}},{"t_ms":13250,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Opening hotel page"}},{"t_ms":13600,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Opening hotel page"}},{"t_ms":13950,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Opening hotel page"}},{"t_ms":14300,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Opening hotel page"}},{"t_ms":14650,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Opening hotel page"}},{"t_ms":15000,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Opening hotel page"}},{"t_ms":15350,"event":"agent_progress","data":{"run_id":"mock_run_h3_booking","step_text":"Opening hotel page"}},{"t_ms":15700,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Selecting room"}},{"t_ms":16050,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Selecting room"}},{"t_ms":16400,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Selecting room"}},{"t_ms":16750,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Selecting room"}},{"t_ms":17100,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Selecting room"}},{"t_ms":17450,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Selecting room"}},{"t_ms":17800,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Entering guest details (dummy)"}},{"t_ms":18150,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Entering guest details (dummy)"}},{"t_ms":18500,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Entering guest details (dummy)"}},{"t_ms":18850,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Entering guest details (dummy)"}},{"t_ms":19200,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Entering guest details (dummy)"}},{"t_ms":19550,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Entering guest details (dummy)"}},{"t_ms":19900,"event":"agent_progress","data":{"run_id":"mock_run_h1_cleartrip","step_text":"Reached payment page, stopping"}},{"t_ms":20250,"event":"agent_progress","data":{"run_id":"mock_run_h1_agoda","step_text":"Reached payment page, stopping"}},{"t_ms":20600,"event":"agent_progress","data":{"run_id":"mock_run_h1_booking","step_text":"Reached payment page, stopping"}},{"t_ms":20950,"event":"agent_progress","data":{"run_id":"mock_run_h2_cleartrip","step_text":"Reached payment page, stopping"}},{"t_ms":21300,"event":"agent_progress","data":{"run_id":"mock_run_h2_agoda","step_text":"Reached payment page, stopping"}},{"t_ms":21650,"event":"agent_progress","data":{"run_id":"mock_run_h3_cleartrip","step_text":"Reached payment page, stopping"}},{"t_ms":22150,"event":"agent_done","data":{"run_id":"mock_run_h2_booking","offer_id":"h2_booking","status":"blocked"}},{"t_ms":22650,"event":"agent_done","data":{"run_id":"mock_run_h3_cleartrip","offer_id":"h3_cleartrip","status":"verified"}},{"t_ms":23150,"event":"agent_done","data":{"run_id":"mock_run_h1_cleartrip","offer_id":"h1_cleartrip","status":"verified"}},{"t_ms":23650,"event":"agent_done","data":{"run_id":"mock_run_h2_cleartrip","offer_id":"h2_cleartrip","status":"verified"}},{"t_ms":24150,"event":"agent_done","data":{"run_id":"mock_run_h2_agoda","offer_id":"h2_agoda","status":"verified"}},{"t_ms":24650,"event":"agent_done","data":{"run_id":"mock_run_h1_agoda","offer_id":"h1_agoda","status":"verified"}},{"t_ms":25150,"event":"agent_done","data":{"run_id":"mock_run_h1_booking","offer_id":"h1_booking","status":"verified"}},{"t_ms":25650,"event":"agent_done","data":{"run_id":"mock_run_h3_booking","offer_id":"h3_booking","status":"unverified"}},{"t_ms":26550,"event":"ranking_ready","data":{"hero_hotel_id":"h1"}}]}
```
