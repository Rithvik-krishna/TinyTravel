# TinyTravel — Full Build Plan

**Tagline:** The price you see isn't the price you pay.
**Event:** Swim with TinyFish, Bangalore — 31 Oct 2026, build window ~11:00–17:00, 4-person team
**One-liner:** TinyTravel sends autonomous TinyFish agents through real hotel checkouts (as a guest, never paying), proves the true all-in price with evidence, filters out unfair comparisons, and hands the user a ready-to-pay link.

---

## 0. Ground rules

1. **One flawless end-to-end flow beats many half-working features.** Pipeline first, polish later.
2. **Never fabricate a price.** No evidence = `unverified`. Never convert unknown into a positive result.
3. **Safety:** guest checkout only, dummy details, stop at the payment page, never pay, never log in, never enter OTP, never store passwords or card data.
4. **Say only what we observed.** "Price moved ₹4,120 → ₹4,390 in 4 min." Never claim a cause (device, location, etc).
5. **Map the official problem statement to features at 11:00** before locking scope. If it doesn't fit, adapt the same engine (fallback ideas: procurement BOM→cart, rental truth, injection range).
6. Don't pre-build the project before the event. Prep accounts, repo shell, API keys, UI shell only.

---

## 1. What the feasibility probes proved (hotel, Bengaluru, 20–21 Nov 2026, 2 adults)

| Site | Reached payment as guest | Steps | Time | Est. cost | Notes |
|---|---|---|---|---|---|
| Cleartrip | YES | 18 | 153s | ~$0.29 | Best performer. Fees reconcile: 15,639 + 1,971 − 4,692 − 2,737 + 1,095 = ₹11,276. Listing ₹8,210 → payable ₹11,276 (+37%). Convenience fee ₹1,095. |
| Agoda | YES | 23 | 268s | ~$0.37 | Respects `currency=INR` URL param. Pressure messages: "last 3 rooms", "price may change". |
| Booking.com | YES | 23 | 297s | ~$0.37 | Returned USD; first run picked single-occupancy room (fixed after prompt update). |
| EaseMyTrip | NO (reached room step) | 10 | 412s | ~$0.16 | Date picker too slow; timed out. Fixable with a better direct URL. |
| MakeMyTrip | NO | 36 | 290s | ~$0.58 | Blank 200 shell on `lite` profile. **`stealth` profile untested.** |
| Goibibo | NO | 35 | 300s | ~$0.56 | Same group protection as MMT. **`stealth` untested.** |

**Implications**
- Demo platforms: **Cleartrip, Agoda, Booking.com** (+ MMT/Goibibo/EMT only if retests pass).
- A run takes 2.5–5 min. A full live demo of many runs is NOT possible → see Demo Mode (section 11).
- `agent_config.max_steps` is closed beta on our account → cap steps via prompt + client timeout. Ask organisers for beta access.
- Each site returned a different hotel → we must target **the same named hotel** across platforms.
- Prices must be recorded at every step with currency as shown. Never convert ourselves.

---

## 2. Scope

### Must build (P0)
1. Search intake (one sentence → editable chips → structured request)
2. Discovery of candidate hotels on 3 platforms
3. Same-hotel matching (dedupe) + room/package normalization (hard filters)
4. Autonomous checkout verification with full `price_trail`
5. Evidence per price (screenshot or recording link, timestamp, source URL)
6. Live investigation dashboard with streaming tiles (blocked/unverified shown honestly)
7. Verdict: **cheapest verified** + **safe-cheapest** (free cancellation) + **best for you**
8. Handoff Pack (deep link, QR, selection card, copy-paste details)

### Build next (P1)
9. 5-step onboarding (Travel DNA) with Skip
10. Fee Leak % + pressure badges
11. Transparency score (0–100, observed on this run)
12. Re-check price button (real drift)
13. Dashboard summary strip

### Only if time (P2)
14. Evidence PDF / shareable report + "report this fee" draft
15. Fee tooltips (GST, convenience fee, resort fee)
16. Price history across runs

### Not building
Price watch cron, flights/rentals, real account login, autonomous booking, loyalty, negotiator, direct hotel sites, image-hash dedupe.

---

## 3. User journey (user-oriented)

| Step | Experience |
|---|---|
| 0. Onboarding (skippable) | 5 chip screens (~30s): who's travelling, budget/night, type & rating, must-haves, booking style + "What is a good deal? Lowest price / Best value / Most transparent" |
| 1. Ask | One sentence: "Bengaluru, 20–21 Nov, 2 people, breakfast, free cancellation, under ₹5k" → parsed into editable chips |
| 2. Wait | Live browser tiles + plain line: "Checking 3 sites like a real buyer. ~3–5 min." |
| 3. Verdict | One card: **"Book Hotel X on Cleartrip. You'll pay ₹4,069, not the ₹3,499 shown."** + "Show proof" |
| 4. Trust | Fee explainer ("convenience fee ₹1,095 = 13% of price"), warnings (non-refundable, pressure messages) |
| 5. Book | **Handoff Pack:** QR to phone, deep link, selection card (room/meal/cancellation/expected price), copy-paste details. User logs in and pays themselves. |
| 6. Final check | **Re-check before paying** → "₹X → ₹Y" |

Demo persona: **Priya**, student booking for visiting parents, wants cheap but refundable.

---

## 4. Architecture

```
Next.js UI  ──►  API (FastAPI or Next routes)  ──►  Orchestrator
                                                      │
        ┌─────────────────────────────────────────────┤
        ▼                    ▼                          ▼
 Discovery (TinyFish)   Checkout probes (TinyFish)   Re-check
        │                    │                          │
        ▼                    ▼                          ▼
   Listings DB  ──► Dedupe ──► Normalize ──► Evidence store
                                   │
                         Price engine + Ranking
                                   │
                    SSE stream ──► Live dashboard / Verdict / Handoff
```

### Pipeline stages
1. **Intake:** LLM parses sentence → JSON → validate (Zod/pydantic): dates in future, guests ≥1, budget > 0.
2. **Discovery:** one extraction run per platform on a pre-filled listing URL, return top ~8 listings (name, area, shown price, rating, URL). No checkout here.
3. **Dedupe:** group listings that are the same hotel (section 7). Select up to **3 target hotels** present on ≥2 platforms (prefer 3).
4. **Normalization / hard filters:** only comparable offers go forward (section 7).
5. **Checkout verification:** one agent per (hotel × platform), guest flow to payment page, return strict JSON + price_trail + evidence.
6. **Price engine:** Fee Leak %, transparency score, ranking.
7. **Handoff:** build deep link + QR + selection card.
8. **Re-check:** re-run one offer (same hotel/room) and diff the price_trail.

### TinyFish usage (per the probes)
- Python SDK (`tinyfish`) was used successfully: `c.agent.stream`, `c.runs.get`, `c.wallet`; auth via `TINYFISH_API_KEY` env var.
- Browser profiles: `lite` (default, fastest) and `stealth` (anti-bot, ~10–20% slower).
- Streaming: each run exposes a `streaming_url` → embed as live tile.
- Recommendation: reuse `probe.py` as the base for the agent service.

---

## 5. Data contracts (shared by all 4 members)

### 5.1 SearchRequest
```json
{
  "destination": "Bengaluru",
  "area_hint": "HSR Layout / Koramangala",
  "check_in": "2026-11-20",
  "check_out": "2026-11-21",
  "guests": 2,
  "rooms": 1,
  "budget_per_night": 5000,
  "must_have": { "breakfast": true, "free_cancellation": true, "parking": false, "wifi": true },
  "deal_mode": "lowest_price | best_value | most_transparent",
  "currency": "INR"
}
```

### 5.2 Listing (discovery output)
```json
{
  "listing_id": "cleartrip_001",
  "platform": "Cleartrip",
  "hotel_name": "La Marvella",
  "address": "string|null",
  "area": "string|null",
  "lat": null, "lng": null,
  "phone": null,
  "rating": null,
  "shown_price": 8210,
  "currency": "INR",
  "source_url": "https://...",
  "captured_at": "ISO-8601"
}
```

### 5.3 ProbeResult (checkout verification output — force the agent to return exactly this)
```json
{
  "site": "",
  "reached_payment_page": true,
  "furthest_step": "search|listing|room|traveller_details|payment|blocked",
  "blocker": null,
  "hotel_name": "",
  "hotel_url": "",
  "room_type": "",
  "max_occupancy": 2,
  "meal_plan": "",
  "cancellation_policy": "",
  "price_shown_on_listing": null,
  "price_shown_on_room_selection": null,
  "price_final_payable": null,
  "fee_lines": [{ "label": "", "amount": 0 }],
  "preselected_addons": [""],
  "urgency_or_scarcity_messages": [""],
  "price_trail": [{ "step": "", "amount": 0, "currency": "" }],
  "currency": "INR",
  "notes": ""
}
```
Server adds: `run_id`, `streaming_url`, `started_at`, `finished_at`, `steps`, `cost_usd`, `evidence[]`, `status` (`verified | unverified | blocked`).

**Verification rule:** `status = verified` only if `reached_payment_page == true` AND `price_final_payable != null` AND at least one evidence item exists AND `fee_lines` reconcile with `price_final_payable` (tolerance ±1%). If lines don't reconcile, keep verified-price but flag `reconciliation: "mismatch"`.

### 5.4 Evidence
```json
{ "type": "screenshot|recording|page_text", "url": "", "step": "listing|room|traveller|payment", "captured_at": "", "extracted_value": 0, "currency": "INR" }
```

### 5.5 TravelProfile (onboarding)
```json
{
  "traveller_type": "solo|couple|friends|family|business",
  "budget_min": 0, "budget_max": 0,
  "hotel_type": "any|budget|business|boutique|luxury", "min_rating": null,
  "must_have": ["breakfast","wifi"],
  "prefers_refundable": true,
  "deal_mode": "lowest_price|best_value|most_transparent"
}
```

### 5.6 HandoffPack
```json
{
  "offer_id": "",
  "platform": "Cleartrip",
  "deep_link": "https://...",
  "qr_png_base64": "",
  "selection_card": { "hotel": "", "room_type": "", "meal_plan": "", "cancellation": "", "dates": "", "guests": 2, "expected_final_payable": 0, "currency": "INR", "verified_at": "" },
  "copy_paste": { "name": "", "email": "", "phone": "" },
  "disclaimer": "Price verified at <time>. Re-check before paying; prices can change."
}
```
Note: a deep link may not restore the agent's cart. It opens the hotel/search on that platform; the selection card tells the user exactly which room to pick and which price to expect.

### 5.7 API endpoints and SSE events
```
POST /api/search                 -> { search_id }
GET  /api/search/:id/stream      -> SSE
GET  /api/search/:id/results     -> verdicts + offers
POST /api/offers/:id/recheck     -> { recheck_id }
GET  /api/offers/:id/handoff     -> HandoffPack
```
SSE event types: `parsed`, `discovery_started`, `listings_found`, `hotels_grouped`, `agent_started {run_id, platform, hotel, streaming_url}`, `agent_progress {run_id, step_text}`, `agent_done {run_id, status}`, `ranking_ready`, `error`.

---

## 6. Agent goal template (checkout probe)

```
Open the provided URL. Search for hotels in {city} for {check_in} to {check_out}, {guests} adults, {rooms} room.
Find the hotel named "{hotel_name}" (exact name; if not found, return blocker "other" with notes).
Select the cheapest room that fits {guests} adults. Prefer free cancellation; otherwise cheapest, and report the cancellation policy.
Proceed as a GUEST through checkout using: Name "Test Guest", email "test.guest+probe@example.com", phone "9000000000".
Record the displayed total at each step in price_trail with the currency shown on screen. Do not convert currencies.
Record every fee line, pre-selected add-on, and any urgency/scarcity message.
STOP at the payment page. Never enter payment details, never click pay/confirm/book, never log in, never enter an OTP, never create an account.
If blocked (login, OTP, captcha, empty page), stop and return the blocker.
Use at most 25 steps. Return ONLY JSON in the given schema.
```
Per-site: pre-filled direct search URLs (tested in probes: Agoda `currency=INR`, Cleartrip query params). For re-checks, use the captured `hotel_url` and the same room/meal/cancellation.

---

## 7. Matching and normalization

### Dedupe (same hotel)
- Signals: name similarity (rapidfuzz token-sort ratio), area/address similarity, phone match, geo distance if coordinates are captured.
- Confidence: **≥0.90 auto-merge**, **0.75–0.89 suggested** (shown as "possible match", not merged in pricing), **<0.75 separate**. Calibrate thresholds on actual probe data.
- UI shows *why* ("Name 94%, same area, phone match").
- Skip image hashing.

### Normalization (comparable offers only)
Compare only if equal on: guests/occupancy, dates/nights, meal plan, cancellation category (free / partial / non-refundable). If not equal:
- Show a clear note ("Booking.com room is non-refundable; not comparable with Cleartrip's free-cancellation room").
- Never silently compare different products.
- Offer both: **cheapest verified** (any policy) and **safe-cheapest** (free cancellation).

---

## 8. Scoring

### 8.1 Fee Leak %
```
fee_leak_pct = (price_final_payable - price_shown_on_listing) / price_shown_on_listing * 100
```
Show next to the fee lines (e.g., convenience fee as % of the listing price). Label as "observed on this run".

### 8.2 Transparency score (0–100, per offer, observed only)
| Component | Weight | Rule |
|---|---|---|
| Fee leak | 50 | 0% leak = 50; linear to 0 at ≥40% leak |
| Add-ons & pressure | 20 | −5 per pre-ticked add-on, −5 per urgency message, floor 0 |
| Price stability on re-check | 20 | unchanged = 20; scaled down by % change; not re-checked = N/A, weights re-normalized |
| Evidence completeness | 10 | listing + room + payment evidence = 10 |

Unverified/blocked offers show **N/A**, never a score. Tap to see the breakdown. Do not treat a high price as a low score, and do not label platforms as "dishonest".

### 8.3 Ranking (after hard filters)
| Mode | Price | Prefs match | Cancellation | Quality* | Transparency |
|---|---|---|---|---|---|
| Lowest price | 60 | 15 | 15 | 0 | 10 |
| Best value | 35 | 25 | 20 | 10 | 10 |
| Most transparent | 25 | 15 | 15 | 0 | 45 |

*Quality only if rating was captured; otherwise re-normalize. Price score uses final payable per night among comparable offers. Show the score breakdown for every recommendation.

### 8.4 Three outputs
1. **Cheapest verified** (lowest verified payable)
2. **Safe-cheapest** (lowest verified payable with free cancellation)
3. **Best for you** (ranking by the user's deal mode)

---

## 9. Screens

1. **Onboarding** — 5 chip steps, Skip, deal-mode choice
2. **Search** — sentence box → editable chips → "Verify prices"
3. **Investigation (hero)** — live `streaming_url` tiles, per-agent status (navigating / price extracted / verified / blocked), counters: listings found, unique hotels, verified, blocked, average fee leak
4. **Hotel comparison** — grouped hotels, "why grouped", comparable offers table, non-comparable warnings
5. **Price evidence** — price trail per offer, fee lines, click any number → screenshot/recording, timestamp, source URL
6. **Verdict + Handoff** — three verdict cards, QR + deep link + selection card + copy-paste details, **Re-check before paying**

Mobile-first layout. Dark/light safe. Blocked results must be visible (no fake success).

---

## 10. Tech stack and repo

| Layer | Choice |
|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind, lucide-react |
| Backend | Python FastAPI (reuse `probe.py` + TinyFish Python SDK) or Next API routes if the team prefers one language |
| Agents | TinyFish Agent (`lite`; `stealth` for MMT/Goibibo retest) |
| Streaming | SSE (backend → UI), `streaming_url` iframes |
| DB | SQLite or Supabase Postgres (keep minimal) |
| Evidence storage | local `/evidence` folder or Supabase Storage |
| Matching | rapidfuzz |
| QR | `qrcode` lib |
| Validation | pydantic / Zod |
| Secrets | `.env` + `.gitignore` (done), never log keys |

```
tinytravel/
├── web/                 # Next.js
│   ├── app/(onboarding|search|investigation|compare|evidence|verdict)/
│   └── components/{LiveTile,PriceTrail,VerdictCard,HandoffPack,EvidenceModal}.tsx
├── api/
│   ├── main.py
│   ├── agents/{discovery.py,checkout.py,recheck.py}
│   ├── services/{tinyfish.py,dedupe.py,normalize.py,scoring.py,handoff.py,evidence.py}
│   ├── schemas.py
│   └── db.py
├── results/             # probe outputs
├── fixtures/            # saved real runs for Demo Mode
├── .env  .gitignore
└── README.md
```

---

## 11. Demo Mode (important: runs take 2.5–5 min)

- **Live segment:** 1 hotel × 3 platforms in parallel (≈3–5 min). Kick it off at the start of the pitch and narrate while tiles run. Must be rehearsed.
- **Full comparison view:** results of an earlier real investigation (3 hotels × 3 platforms), clearly labelled with its capture timestamp ("Saved run, 10:42 AM").
- Record one full run tonight/early morning as a fixture. Never present saved data as live.
- Check TinyFish concurrency limits early. If 9 parallel runs are allowed and fit the budget, run the full set live; otherwise use the split above.
- Freeze features at 16:00.

---

## 12. Budget

| Item | Estimate |
|---|---|
| Discovery (3 platforms) | ~$0.6 |
| Checkout (9 runs @ ~$0.35) | ~$3.2 |
| One full investigation | **~$3.8** |
| Re-check (1 run) | ~$0.35 |
| Probe spend so far | ~$2.32, balance ~$11.52 (from probe log) |

Plan: max 2 full investigations before the pitch (the fixture run + one dress rehearsal), single-hotel tests otherwise. Teammates each hold their own TinyFish credits; split keys if needed. Costs are estimates from steps × ~$0.016; verify in the dashboard.

---

## 13. Team split

| Member | Owns | Key deliverables |
|---|---|---|
| **M1 Agent lead** | TinyFish integration | discovery + checkout + recheck agents, goal prompts, schemas, `streaming_url`, run orchestration, concurrency/timeouts |
| **M2 Backend/intelligence** | Data & logic | dedupe, normalization, price engine, scoring, ranking, handoff builder, DB |
| **M3 Frontend lead** | UI | onboarding, search chips, live tiles, comparison, evidence modal, verdict, mobile layout |
| **M4 Integration/product/pitch** | Glue & story | API contracts, SSE wiring, evidence capture, fixtures/demo mode, testing, 3-min script, README, submission |

Rules: freeze contracts (section 5) by 11:30; UI uses clearly-labelled mock data only until real data lands; stable `demo` branch; no one edits another's core files without a ping.

---

## 14. Timeline (11:00–17:00)

| Time | Goal | Gate |
|---|---|---|
| 11:00–11:20 | Read problem statements, map to features, lock scope | Scope signed off |
| 11:20–11:50 | Contracts, repo, env, run MMT/Goibibo `stealth` retest in background | Contracts frozen |
| 11:50–13:00 | M1: checkout agent on target hotel · M2: dedupe/normalize on probe data · M3: search + live tile shell · M4: SSE + evidence storage | — |
| 13:00–14:00 | Wire **one hotel end to end**: discovery → match → checkout → evidence → price | **14:00 GATE: one real hotel verified end to end.** If not, cut P1 and fix. |
| 14:00–15:00 | Ranking, verdict cards, Handoff Pack + QR, evidence modal | — |
| 15:00–15:45 | Onboarding, Fee Leak %, transparency score, dashboard strip, re-check | — |
| 15:45–16:00 | **FEATURE FREEZE.** Record fixture run | — |
| 16:00–16:40 | Test 10+ queries, fix failures, pick demo query (stable), mobile check | — |
| 16:40–17:00 | Rehearse 3-min pitch twice, final deploy/branch | — |

### Cut order if behind
1. Dashboard stats → 2. Transparency score breakdown → 3. Onboarding steps 3–5 (keep budget + must-haves) → 4. Re-check → 5. Fee tooltips/PDF. **Never cut:** end-to-end verification, evidence, honest blocked states, Handoff Pack.

---

## 15. Risk register

| Risk | Prevention |
|---|---|
| Site blocks automation | Only use platforms proven in probes; `stealth` retest for MMT/Goibibo; show `blocked` honestly |
| Login/OTP wall | Guest flows only; stop at the first wall and mark unverified |
| Runs too slow for live demo | Demo Mode (live 1×3 + labelled saved run); pre-filled URLs; step cap in prompt |
| Different hotel/room across platforms | Target exact hotel name; normalization + hard filters |
| Prices don't reconcile | Capture price_trail + fee_lines; reconciliation check; don't call a "leak" unless it reconciles |
| Wrong dedupe | Conservative thresholds, show reasons, suggested matches not auto-priced |
| Credits run out | Budget table, ≤2 full runs pre-pitch, teammates' keys |
| API timeout / agent hangs | Client timeout (~6 min), explicit failure status, no retry loops |
| Price changes between runs | Timestamp everything, "verified at HH:MM", re-check button |
| Key leaked | `.env` + `.gitignore`; revoke at agent.tinyfish.ai/api-keys if exposed |
| Legal/ethical questions | Dummy data, never pay, polite rate, "observed" wording; say it in the pitch |

---

## 16. Pitch (3 min) and Q&A

| Time | Beat |
|---|---|
| 0:00–0:15 | Hook: "Same hotel, three apps, three prices. One changed while we watched." |
| 0:15–0:30 | Meet Priya and TinyTravel (one sentence) |
| 0:30–1:45 | Live run: sentence → chips → 3 browser tiles race to checkout; counters tick; narrate the guest flow |
| 1:45–2:25 | Reveal: click a price → screenshot/recording proof; Fee Leak %; non-comparable room flagged |
| 2:25–2:50 | Verdict cards → QR to phone → Handoff Pack → Re-check |
| 2:50–3:00 | Close: "We found the real cheapest price. You pay in one tap. We never see your password." |

**Expected questions**
- *Do you pay or book?* No. Dummy data, stop at the payment page.
- *Why agents, not scraping?* The payable price only appears after multi-step interaction on dynamic pages.
- *Hallucinations?* Strict schemas, deterministic math, evidence required, unverified when unsure.
- *What if a site blocks you?* Shown as blocked/unverified, never invented.
- *How do you avoid wrong comparisons?* Dedupe with reasons + normalization into comparable offers.
- *Privacy?* No passwords, no card data; only name/email/phone for the user's own copy-paste pack.
- *Scalability?* Same engine = flights, rentals, e-commerce; hotels first.

---

## 17. Open items to verify (do early, they change the build)

- [ ] **Screenshots:** the probes returned JSON + stream links, not screenshots. Confirm how to capture evidence (API output, Browser session, or recording link). Until confirmed, evidence = recording link + extracted values + timestamp.
- [ ] **MMT/Goibibo with `stealth`:** one retest each (~$0.55 each).
- [ ] **Same-hotel test:** pick one HSR hotel on Cleartrip + Agoda + Booking.com; capture the full price_trail on all three.
- [ ] **Concurrency limit:** how many parallel agent runs are allowed?
- [ ] **`max_steps` beta:** ask organisers for access.
- [ ] **Human takeover:** does TinyFish support handing a live session to the user? (Would upgrade the Handoff Pack.)
- [ ] **Hotel deep links:** confirm `hotel_url` returned by agents opens the right property with dates prefilled.
- [ ] **Judging criteria:** ask organisers; tune the pitch.
- [ ] **Problem-statement fit:** confirm at 11:00.

---

## 18. Checklist

**Before the event**
- [ ] Everyone signed up via the referral link; test prompt run in Claude/ChatGPT
- [ ] `.env` + `.gitignore` in place; keys never committed
- [ ] Repo + contracts doc + UI shell ready (no project logic)
- [ ] Laptops, chargers, hotspot, QR scanner on phone

**Definition of done (demo)**
- [ ] One real hotel verified end to end on 3 platforms with price_trail + evidence
- [ ] Blocked/unverified states render correctly
- [ ] Verdict cards + Handoff Pack + QR work on a phone
- [ ] Re-check works on one offer
- [ ] Fixture run saved and labelled
- [ ] Pitch rehearsed twice, demo query stable on 10+ attempts
