# TinyTravel — Master Plan (Startup Edition) — v2

> Last updated: 13 Nov 2026 (v2; supersedes the 10 Nov version)
> Audience: every teammate and every coding agent (Antigravity, Claude, etc.) working on TinyTravel.
> Purpose: one document that explains what we built, what we are building next, every feature and **why we chose it**, what we rejected and why, the rules we never break, and how the pieces fit together.
>
> If something here conflicts with a chat message or an old prompt, **this document wins** until it is edited. Section 4 describes what actually exists today; sections 5–16 describe the target product.
> Section numbers are kept stable across versions so existing references ("see §9", "§4.7") still work.

---

## 0. How to use this document

| If you are… | Read first |
|---|---|
| A new teammate | §1, §2, §3, §8, §12 |
| Working on backend/agents | §4, §6 (F1–F6), §9, Appendix A–C |
| Working on frontend | §3, §4.4–4.6, §6 (F1, F2, F7), Appendix A |
| Working on data/cache | §6 (F3, F5, F6), §10 |
| Writing the application or pitch | §1, §2.4, §2.5, §3, §10, §11, §12, Appendix E |
| A coding agent | §9 (rules) + §4 (current state) + the feature section you are assigned |

**Which parts are pitch and which are engineering**

- **Strategy / pitch parts:** §1, §2, §3, §8, §10, §11, §12, §13, §14, §15, Appendix E.
- **Engineering / agent-rules parts:** §4, §5, §6, §9, Appendices A–D.
- If this file grows further, split it along that line: a short strategy doc and a technical/agent-rules doc.

**Status labels used throughout**

- **EXISTS** — built, merged, tested in this repo.
- **PARTIAL** — built but not validated live, or only in fake/mock mode.
- **PLANNED** — designed here, not built.
- **DROPPED** — considered and rejected (with reasons in §7).

**Evidence labels used for numbers (new in v2)**

- **Measured** — we observed it on a real run and can point to the artifact.
- **Estimated** — derived from assumptions; replace with measured numbers.
- **Unverified claim** — taken from an outside source; must be checked before external use (list in §16b).

---

## v2 change log (what changed since 10 Nov and why)

| # | Change | Why |
|---|---|---|
| 1 | **Positioning reframed** from "price comparison" to "the verified all-in price layer for hotel booking" (§1.1) | "Comparison" puts us against Google Hotels, MakeMyTrip, Skyscanner. A verified-price layer is a different category: consumer app, B2B data and API all follow from it. |
| 2 | **Evidence dataset plan added** (§2.4) | One run on one hotel (+34.6%) is an anecdote. We need N checkouts across hotels and platforms for a defensible headline. |
| 3 | **Competitive landscape added** (§2.5) | The plan had no named alternatives. Judges will ask. |
| 4 | **Distribution answer made explicit; extension (F9) moved up** (§1.2, §8) | "Why would a user come to us?" was the biggest gap. The extension is the best answer. |
| 5 | **B2B-first revenue story** (§10.1, §10.4) | The doc's own math shows consumer affiliate loses money per comparison. Subscriptions for travel businesses lead; consumer is the funnel. |
| 6 | **Moat metric defined** (§10.6) | Investors want one number that shows the data asset compounding. |
| 7 | **Measured vs estimated table** (§10.2b) | Several numbers (cost per run, hybrid-agent speed) are still estimates and were mixed with measured ones. |
| 8 | **Unverified claims isolated** (§16b) | Affiliate rates, drip-pricing regulation wording and the Agoda run-2 result must be verified before public use. |
| 9 | **Submission scope trimmed** (§12.3–§12.4) | 14 features reads as unfocused. Core loop leads; the rest is one roadmap slide. |
| 10 | **Inconsistencies fixed** (§2.2, §4.10, §15) | Two different La Marvella probes were quoted without explanation; "Phase 0 done" contradicted the known-issues list. |
| 11 | **Customer validation made a dated deliverable** (§13.1) | One validated customer beats ten ideas; it is also our weakest judging criterion (market viability). |

---

## 1. One-paragraph summary

**TinyTravel verifies the real, final, all-in price of the same hotel on several booking sites, proves it with evidence, compares like for like, and tells the user where to book — so they stop opening five tabs and clicking through five checkouts to discover that the price they saw is not the price they pay.**

- **One-liner (v2):** "TinyTravel is the verified all-in price layer for hotel booking: the real payable price on every site, with proof behind it."
- **Consumer line (kept):** "Stop checking five sites. We find the real final price of the same hotel everywhere, prove it, and tell you where to book."
- **Tagline (kept from the hackathon):** "The price you see isn't the price you pay."
- **What makes it hard (and valuable):** the payable price only appears at the *end* of a multi-step checkout (taxes, convenience fees, add-ons, coupons). You cannot get it by scraping listing pages. Software has to actually walk the checkout.
- **What makes it a startup instead of a demo:** we turn one-off, expensive checkout walks into a **shared, cached price database with signed proof**, keep the **comparison** as the thing users see, and monetise through **B2B subscriptions first**, then savings-based pricing, affiliate handoff and (later) an API for AI agents.

### 1.1 Positioning (new in v2)

| | Old framing | New framing |
|---|---|---|
| Category | Price comparison app | Verified all-in price layer (data + proof), with a consumer app on top |
| Competes with | Google Hotels, MakeMyTrip, Skyscanner, meta-search | Nobody directly: they show pre-checkout prices; we verify post-checkout prices |
| Customers | Travellers | Travel agents / corporate desks (pay), travellers (free funnel), later AI agents (API) |
| Moat | "A good UI" | The verified-price database, signed evidence, playbook library, crowd data |

**Rule for the pitch:** lead with the problem and the proof, then position as the verified-price layer. Do not call ourselves a "comparison site" in the first sentence.

### 1.2 Why would a user (or business) come to us? (new in v2)

This is the question the plan most needed to answer. Our answer has three parts:

1. **Consumers: meet them where they shop.** The browser extension (F9) shows the true all-in price and cross-site comparison inside the booking page they are already on. We do not need to win the "where do I start my search" habit.
2. **Businesses: sell time and proof.** Travel agents and corporate desks quote hotels in bulk, lose hours comparing checkouts, and need evidence for clients. They pay for speed and receipts (F11).
3. **Everyone: the answer is instant because of the cache.** The first verification is slow; the next user gets it in seconds (F3).

### The three layers (this framing is the most important idea in the doc)

1. **The Face — what users see and pay attention to.**
   Same-hotel matching across sites → listed vs final price per site → fair (like-for-like) comparison → a clear "book here" verdict → handoff to the winning site.
2. **The Engine — what makes the face fast, cheap and believable.**
   Price database + cache + scheduler, our own hybrid agent, tiered verification with a live re-check before payment, signed evidence receipts.
3. **Growth & Money — why it is a business.**
   B2B subscriptions and evidence reports, browser extension + crowd data, price-drop alerts/rebooking, outcome-based pricing, AI-agent API, vertical expansion.

> **Correction we made during planning:** at one point the idea ranking pushed the comparison down the list as if it was "already done". That was wrong. The comparison **is** the visible product. Everything else exists to make it cheaper, faster, more trustworthy, or more profitable. If a feature does not feed or monetise the comparison loop, it does not belong in the core build.

---

## 2. The problem

### 2.1 What the user experiences

A user wants to book a hotel room in a city on given dates. To find the best deal they must:

1. Search several sites (Cleartrip, Agoda, Booking.com, MakeMyTrip, …).
2. Match the same property across sites (names and listings differ).
3. Click through each checkout to discover the true payable amount (taxes, fees, discounts, coupons).
4. Realise that rooms are not the same product (single vs double occupancy, breakfast, refundable vs non-refundable).
5. Repeat when prices change.

This wastes time, and the listed price is routinely different from the final price.

### 2.2 Our own evidence (real runs)

There are **two separate probes of the same hotel**. Do not mix them:

| Probe | Hotel / stay | Listed | Final payable | Observed gap | Where it is used |
|---|---|---|---|---|---|
| **Earlier probe** | La Marvella, Bengaluru, Cleartrip | ₹8,210 | ₹11,276 | +37.3% | Baked into the demo fixture (`fixtures/demo_run.json`) |
| **Gate run, 31 Oct 2026** | La Marvella, Bengaluru, 20–21 Nov 2026, 2 guests, Cleartrip | **₹8,867** | **₹11,933** | **+34.6%** | **Use this one externally** (real, reconciled) |

Gate-run fee lines reconcile exactly: 15,639 (room) + 1,971 (taxes) − 4,692 (discount) − 2,080 (coupon) + 1,095 (convenience fee) = **₹11,933**.

> Important wording rule (see §9): this is an **observed difference on this run**. We never claim *why* it happened, and we separate **taxes** (not a "hidden fee") from **platform/property fees** and **add-ons**.

> **Limitation (v2):** this is n = 1 hotel on 1 platform. It is an anecdote until §2.4 is done. Present it as "the largest observed case", not as the typical gap.

### 2.3 Why the obvious solutions fail

| Approach | Why it fails |
|---|---|
| Scrape listing pages | Final price is not on the listing page. |
| Use meta-search sites | They show listing prices too, often without final taxes/fees. |
| Official APIs/affiliate feeds | Mostly give listing/net rates, not the checkout's final payable; access requires partnerships. |
| One big LLM browsing agent per user | Slow (3–6 minutes), costly (~$0.4 per checkout, estimated), flaky on anti-bot sites. |
| Let the user do it | The status quo we are replacing. |

### 2.4 Evidence dataset — turning one anecdote into a statistic (new in v2) — PLANNED (do first)

**Goal:** 12–15 (ideally 30) guest checkouts across several hotels and at least 2 platforms, so we can state a median gap with a sample size.

**Protocol (manual is fine; agent runs are optional)**

- Same stay for every check: Bengaluru, 20–21 Nov 2026, 2 adults, 1 room.
- 4–5 hotels that appear on ≥ 2 of Cleartrip, Agoda, Booking.com; mix budget and mid-range.
- Guest only, dummy details, stop at the payment page, never pay (§9.1).
- Same room type and meal plan on every site; otherwise the row is non-comparable.
- One row per hotel × platform with: exact room text, guests, meal plan, cancellation, listed price, taxes, platform/convenience fee, add-ons, discounts/coupons, final payable, currency, time.
- **Gap %** = (final − listed) / listed × 100 (same room only).
- **Gap excluding taxes** = (final − taxes − listed) / listed × 100 (taxes are not a "hidden fee").
- Report: N, median, min–max, count with gap ≥ 10%. **Include small or negative gaps** (coupons can lower the total); never drop them.

**Headline sentence (fill in; do not pre-write the numbers):**

> "Across [N] guest checkouts on [platforms] for [M] Bengaluru hotels (20–21 Nov 2026, 2 guests), the final payable price was a median of [X]% above the listed price ([Y]% excluding taxes); [K] of [N] checkouts differed by 10% or more. Observed on these runs."

**Where the data lives:** `results/evidence_dataset.csv` (committed), with a summary line mirrored into §2.2 once complete.

**Done when.** N ≥ 12 rows, every row reconciles (fee lines sum to final within ±1%), and the headline sentence is filled in with real numbers.

### 2.5 Competitive landscape (new in v2) — to be completed with verified details

> Competitor capabilities below are our working understanding and must be **verified before being stated externally**. The point of the table is to show where we differ, not to criticise anyone.

| Alternative | What it does well | Where the gap is for our user | Our difference |
|---|---|---|---|
| Google Hotels | Huge reach, easy search | Shows prices before full checkout; final payable can differ (verify) | We verify the post-checkout payable and attach proof |
| Meta-search (Skyscanner, Trivago, etc.) | Aggregates many sites | Listing/pre-checkout prices; fees and taxes may appear only at checkout (verify) | Same as above, plus like-for-like room normalisation |
| OTAs themselves (Cleartrip, Agoda, Booking.com, MakeMyTrip) | Direct inventory | Each shows only its own price; no neutral cross-site view | Neutral, cross-site, evidence-backed |
| Travel agents / manual process | Human judgement | Slow, repeated work per quote | We sell them the verified quotes (B2B) |
| Rate-parity / pricing-intelligence tools (hotel-side) | Serve hoteliers | Built for the supply side, not for travellers or agents | We serve the demand side with proof |

**Open item:** name 2–3 real competitors per row and confirm each claim against their product before submission.

---

## 3. Product definition

### 3.1 Core user journey (the loop we must demo)

1. **Search** — "Bengaluru, 20–21 Nov, 2 people, breakfast, free cancellation, under ₹12k" (free text or structured fields).
2. **Discover** — find candidate hotels on each platform.
3. **Match** — group listings that are the same property across platforms (with confidence and a human-readable "why").
4. **Verify** — for the top candidates, find the true all-in payable price per platform (cached if fresh, otherwise via agent).
5. **Normalise** — only compare like for like (same guests/occupancy, nights, meal plan, cancellation category); warn when a room is not comparable.
6. **Decide** — rank and give verdicts: *cheapest verified*, *safest cheapest (free cancellation)*, *best for you*.
7. **Prove** — "Show proof": price trail, fee lines (tax vs fee vs add-on), evidence (recording link + page text), observed-on-this-run labels.
8. **Hand off** — selection card (exactly which room/meal/cancellation to pick and which price to expect), deep link/QR to the winning site, re-check before paying.

### 3.2 Personas

**Priya** (consumer), student, booking a hotel for visiting parents; wants cheap but refundable; has no time to compare five sites.

**Travel desk user** (first paying segment, to be chosen in §13.1): books or quotes many hotels per week, needs all-in prices with proof for clients, values time saved per quote. Candidate segments: independent travel agents, corporate travel desks, event planners. **Pick one before building B2B features.**

### 3.3 What the user sees on the verdict screen

- A side-by-side card per platform for the same hotel: **listed price → final payable → % difference**, cancellation category, meal plan, occupancy.
- A **freshness chip** on every price ("verified N min ago").
- Taxes shown separately from platform/property fees.
- Blocked/unverified platforms shown honestly as "N/A — not verified" (never scored, never shown as 0). These states must look deliberate and trustworthy, not broken.
- One highlighted winner with a one-line reason.
- "Show proof" for each price (price trail, fee lines colour-coded by kind, receipt hash once F6 exists).
- A handoff pack for the winner.

### 3.4 Non-goals (for now)

- We do **not** complete bookings or take payments.
- We do **not** log into user accounts or use real user details in the checkout probe (see §7.1).
- We do **not** claim why prices differ (device, location, etc.).
- We do **not** try to defeat anti-bot protections as a product strategy (see §7.2).

---

## 4. Where we are today (state of the hackathon build) — EXISTS / PARTIAL

> Built at the "Swim with TinyFish" hackathon, Bangalore, 31 Oct 2026 (build window 11:00–17:00, 4-person team) and in the days after. Backend owner: Nikhil. Frontend owner: Rithvik. Coding agent used: Antigravity.

### 4.1 Repository layout

```
tinytravel/
  web/        Next.js frontend (Rithvik)
  api/        FastAPI backend (Nikhil)
    models.py, events.py, main.py, db.py, config.py
    agents/   checkout.py, discovery.py, recheck.py
    services/ tinyfish.py, scoring.py, dedupe.py, normalize.py, evidence.py,
              handoff.py, intake.py, orchestrator.py, fees.py, reporting.py
    tests/
  fixtures/   demo_run.json, sse_script.json, real/ (saved real offers), saved_* (see below)
  scripts/    probe_site.py, e2e_one_hotel.py, record_fixture.py,
              query_suite.py, scan_secrets.py, export_openapi.py
  results/    raw probe/run outputs (+ evidence_dataset.csv, planned, §2.4)
  docs/       BUILD_PLAN.md, PHASED_PLAN.md, CONTRACT.md, EVENTS.md,
              CONTRACT_CHANGES.md, TINYFISH_NOTES.md, GATE_REPORT.md,
              RUNBOOK_FRONTEND.md, FREEZE.md, OWNERSHIP.md, openapi.json
  AGENTS.md   shared rules for any coding agent
```

Git: `main` (stable, PR + green CI), `backend` (Nikhil), `frontend` (Rithvik), `demo` (final tagged branch, not yet created). Repo: `Rithvik-krishna/TinyTravel`. Workflow rules: never force-push, merge `origin/main` into your branch instead of resetting, merge PRs only after CI is green.

### 4.2 Data modes (`DATA_MODE`)

| Mode | What it does | Keys needed |
|---|---|---|
| `mock` | Replays fixtures, no agents | none |
| `fake` | Full pipeline with canned TinyFish outputs (`TINYFISH_FAKE=1`), no spend | none |
| `live` | Real TinyFish agents | TinyFish key |
| `saved` | Replays a recorded **real** run | none |

Notes: `fake` needs `TINYFISH_FAKE=1` as well. `saved` currently returns HTTP 503 because the saved files in the repo are flagged `mock: true` (a real recording has not been made yet) — this is deliberate so fake data can never masquerade as a real saved run. **Recording a real saved run is a top-priority task** (it is the demo safety net, §12.6).

### 4.3 Pipeline (orchestrator)

```
intake (text/fields -> SearchRequest; LLM parse with offline regex fallback)
  -> discovery (per platform, listing extraction only; target mode skips this)
  -> dedupe/group (same-hotel matching)
  -> select targets (>=2 platforms, <=3 hotels, within budget)
  -> checkout verification agents (per hotel x platform; semaphore-limited)
  -> scoring (fee leak, transparency, ranking, verdicts, warnings, summary strip)
  -> results + SSE events + SQLite persistence
```

- **Target mode**: request includes `hotel_name` and `platforms` → skips discovery (used for live demos: 1 hotel × N platforms).
- **Concurrency**: `MAX_CONCURRENT_RUNS` (default 3). **Timeout**: `AGENT_TIMEOUT_S` (default 360; 600 for live runs). **No retries inside code** — a failed run is a failed run.
- **Budget guard**: `MAX_SPEND_USD` per search (default 4.0). Runs that would exceed it are skipped and returned as `unverified` with blocker `other` and a note. `DISABLE_LIVE=1` is a kill switch.
- **Persistence**: SQLite tables `searches`, `offers`, `events` (append-only for SSE replay), `price_history` (real observations only; mock rows excluded unless `include_mock=true`).

### 4.4 API surface (current)

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | health + mode |
| `POST /api/search` | accepts `{text}` or flat fields, optional target mode `{hotel_name, platforms}`; returns `{search_id}` |
| `GET /api/search/{id}/stream` | SSE with late-subscriber replay |
| `GET /api/search/{id}/results` | same shape as `fixtures/demo_run.json`; partial results while running, `complete` flag |
| `GET /api/offers/{id}/handoff` | HandoffPack (selection card, deep link, QR, disclaimer) |
| `POST /api/offers/{id}/recheck` | re-run one offer; max 2 per search; budget- and kill-switch-guarded; takes ~3–5 min live |
| `GET /api/history` | real recorded price observations (empty until real runs exist) |
| `GET /api/fee-glossary` | cautious explanations of fee kinds |
| `GET /api/search/{id}/report` | printable, HTML-escaped evidence report |
| `GET /api/offers/{id}/report-fee-draft` | polite, factual fee-inquiry draft (fees only, not taxes) |
| `GET /evidence/{path}` | static evidence files (path traversal blocked) |

### 4.5 SSE events (in order of a normal run)

`parsed` → `discovery_started` → `listings_found` → `hotels_grouped` → `agent_started {run_id, offer_id, platform, hotel, streaming_url}` → `agent_progress {run_id, step_text}` → `agent_done {run_id, offer_id, status}` → `ranking_ready {hero_hotel_id}`; `error {message, recoverable, code?}` any time.
`agent_started` fires as soon as the live streaming URL exists so the UI tile can open early.

### 4.6 The data contract

- `fixtures/demo_run.json` = the shape of `/results`; `fixtures/sse_script.json` = the shape of the SSE stream. These two files **are** the contract with the frontend.
- `api/models.py` and `api/events.py` are pydantic v2 models with `extra="forbid"` that mirror the fixtures; CI validates fixtures against them. `docs/openapi.json` is exported from the app.
- **Rules:** additive changes only (never rename, remove or retype a field). Any change updates models, fixtures, tests and a dated entry in `docs/CONTRACT_CHANGES.md` in the same commit.
- **Units/semantics:** amounts are JSON numbers in the currency shown on the site (INR for the demo); **never convert currencies**; unknown = `null`, **never 0**; timestamps ISO-8601 with `+05:30`.
- **Enums:** status `verified | unverified | blocked`; cancellation category `free | partial | non_refundable`; blocker `captcha | login | otp | timeout | other | null`; fee kind `tax | platform_fee | property_fee | add_on | other`; deal mode `lowest_price | best_value | most_transparent`.
- Flags: `mock: true` on mock data; `saved: true` + capture timestamp on saved real runs; `complete` on results.
- **Planned additive fields (cache/receipts, do not break the contract):** `captured_at`, `freshness_seconds`, `source` (`own | tinyfish | crowd`), `receipt_hash`, `receipt_url`.

### 4.7 Verification rule (core invariant)

An offer is **verified** only if **all** hold:
1. `reached_payment_page == true`;
2. `price_final_payable != null`;
3. at least one evidence item exists;
4. fee lines sum to `price_final_payable` within ±1% (otherwise `reconciliation = "mismatch"`, keep the price, never call it a verified leak);
5. currency equals the requested currency (else `unverified`, never ranked, with a visible note);
6. the booked room's occupancy fits the guests (else `unverified` / non-comparable — `reached_payment_page` stays as observed, `blocker` stays `null`);
7. fee leak is computed only when the listing price belongs to the **same room** as the final payable (otherwise `null`).

`blocked` is reserved for real obstacles that stopped the run (captcha, login, otp, timeout, other).

### 4.8 Scoring formulas (frozen — do not change without updating golden tests)

- **Fee leak %** = `round((final − listing) / listing × 100, 1)`; label "observed on this run".
- **Transparency score** (verified offers only; else `null`, note "N/A (not verified)"):
  - fee-leak component (max 50) = `max(0, 50 × (1 − leak/40))`
  - add-ons pressure (max 20) = `max(0, 20 − 5×preselected_addons − 5×urgency_messages)`
  - price stability (max 20, only if a re-check exists) = `20 × max(0, 1 − pct_change/10)`
  - evidence (max 10) = 10 if listing + room + payment evidence all exist, else `10 × n/3` (1 decimal)
  - score = `round(sum_present / max_possible × 100)`, max = 80 without stability, 100 with it. Note: "observed on this run" (+ ", stability N/A, weights re-normalised" without a re-check).
- **Ranking** (verified offers only), components 0–100: price = `100 × min_payable / payable`; prefs = `100 × (breakfast + free_cancellation)/2`; cancellation = free 100 / partial 50 / non_refundable 0; quality = `rating/5 × 100` (dropped and weights re-normalised if rating is null); transparency = score.
  Weights `[price, prefs, cancellation, quality, transparency]`: lowest_price 60/15/15/0/10; best_value 35/25/20/10/10; most_transparent 25/15/15/0/45. `total = round(sum(c×w)/sum(w present), 1)`; sort by `(-total, payable, offer_id)`.
- **Verdicts** (overall and per hotel): `cheapest_verified` = lowest payable; `safe_cheapest` = lowest payable with free cancellation (null if none — never a wrong pick); `best_for_you` = top of ranking in scope.
- **Non-comparable warnings:** offers that differ from the majority on guests/occupancy, nights, meal plan or cancellation category get a plain-English warning. We never silently compare different products.
- **Summary strip:** listings found, unique hotels, verified/unverified/blocked counts, average fee leak (verified only).

### 4.9 Same-hotel matching (dedupe) — calibrated

- Normalise names: lowercase, `&` → `and`, strip punctuation and generic suffix noise (hotel, resort, lodge, …), collapse spaces.
- Confidence = weighted blend: **name + area**: `0.75 × name_sim + 0.25 × area_sim`; **name + area + geo**: `0.60 / 0.20 / 0.20`; phone match `+0.15`, phone mismatch `−0.25`. Name similarity = rapidfuzz `token_sort_ratio`.
- Thresholds: `≥ 0.90` merged; `0.75–0.89` **suggested** ("possible match", **not** merged into pricing); `< 0.75` separate.
- Calibration on fixture hotels: La Marvella 0.96 (merged), Lemon Leaf Suites 0.96 (merged), Urban Nest Inn vs Urban Nest Inn & Suites 0.79 (suggested).
- `select_targets`: hotels present on ≥ 2 platforms, up to 3, within budget on shown price, stable order; suggested (unmerged) groups are never selected as multi-platform hotels.

### 4.10 Live results so far (real TinyFish runs)

> Verify the numbers against `fixtures/real/` and `results/` before quoting them externally.

| Platform | Hotel | Outcome | Notes |
|---|---|---|---|
| Cleartrip | La Marvella | **Verified live (measured)** | ₹8,867 → ₹11,933 (+34.6%), fee lines reconcile exactly; 2 runs, about $1.0 total for the gate. |
| Agoda | La Marvella | Run 1: `unverified` (occupancy ambiguity). Run 2: reported **verified**, payable ₹12,936.93, +18.2%, 2 adults — **do not quote externally until re-verified (§16b)** | Run 1 payment page showed a "1 x Executive Twin" room while the agent's own note said that room was rejected; extraction of occupancy was unreliable. Re-verify run 2 evidence: room text must literally show 2 adults; listing price must be the same room. |
| Booking.com | La Marvella | Attempt 1: **timeout** at 360 s (23 steps, no result). Attempt 2: reached payment page but in **USD** ($150.59) with inclusive-tax double counting. Attempt 3 (targeted INR fix): **outcome not confirmed** | A USD offer must be `unverified` and never ranked or converted. Do not run more attempts without a plan. Treat Booking.com as honest `unverified` unless attempt 3 is confirmed. |

Evidence available today: a live **recording/stream link** (may expire) and **page text snippets** saved under `/evidence`. **TinyFish SDK v0.11.0 does not provide downloadable screenshots**, so `page_text` is our durable proof.

Cost observations: roughly 23–30 steps per checkout, about **$0.37–0.48** per run by the estimate `steps × 0.016` (**estimated**; the code's balance reading did not change after live runs, so confirm real spend on the TinyFish dashboard).

### 4.11 Known issues and tech debt (honest list)

1. Booking.com: returns USD, slow, inclusive-tax double counting → needs INR handling and a longer timeout; may remain unverified.
2. Agoda: occupancy/room text extraction unreliable → goal prompt must copy the booked room's guest-count text verbatim from the booking summary.
3. Evidence: stream links can expire; no screenshots. Embedding TinyFish `streaming_url` in an iframe is untested.
4. Cost accounting: estimate only; wallet balance reading looked stale.
5. No real saved run yet → `DATA_MODE=saved` returns 503 until one is recorded.
6. QR test on CI: the `pyzbar` import fallback should be a visible skip, not a silent pass.
7. Fee-inquiry draft says "total observed difference", which includes taxes → label it "(includes taxes)".
8. Discovery has never run live; single-platform comparison is not supported (needs ≥ 2 platforms); target mode is the only live-tested path.
9. Handoff `copy_paste` carries dummy "Test Guest" details — fine for a demo, meaningless for a real booking.
10. Secrets hygiene incident: an API key was once pasted into a command and logs. Rotate, keep keys in `.env` only, never in prompts/commands/chat; `scripts/scan_secrets.py` (including `--git-history`) must stay clean.
11. **(new)** The headline gap (+34.6%) is n = 1; the evidence dataset (§2.4) does not exist yet.

---

## 5. Target architecture (the startup version)

```
                      +----------------------------+
   User (web app) --> |  Comparison API / App      |  <- THE FACE (F1, F2)
   Extension (F9) --> |                            |
                      +-------------+--------------+
                                    |
              cache hit? ----yes--> return price + freshness + proof
                                    |no / stale
                                    v
                      +----------------------------+
                      |  Tiered verification (F5)  |
                      |  1 cheap scan              |
                      |  2 agent on top 2 only     |
                      |  3 live re-check at pay    |
                      +------+---------------+-----+
                             |               |
                  +----------v---+     +-----v-----------+
                  | Own hybrid   |     | TinyFish agent  |
                  | agent (F4)   |     | (fallback)      |
                  | playbooks +  |     +-----------------+
                  | LLM recovery |
                  +------+-------+
                         |
        +----------------v----------------+      +---------------------+
        |  Price database + cache (F3)    | <--- | Crowd observations  |
        |  scheduler, TTLs, price history |      | via extension (F9)  |
        +--------+------------------+-----+      +---------------------+
                 |                  |
        +--------v------+   +-------v--------+
        | Signed        |   | Price-drop     |
        | receipts (F6) |   | watch (F7)     |
        +---------------+   +----------------+
                 |
   Money: B2B + evidence reports (F11), outcome pricing (F8),
          affiliate handoff, AI-agent API (F12), verticals (F13), partnerships (F14)
```

**Design principles**

1. **The comparison is the visible product** (F1/F2). Everything else must feed or monetise it.
2. **Prove it or don't show it.** Every price carries evidence and a timestamp; no evidence = unverified.
3. **Verify once, serve many.** Per-user live verification is a cost trap; a shared cache is the economic engine.
4. **Cheap first, expensive last.** Scans before agents, agents before live re-checks, humans only for money.
5. **Interfaces over vendors.** The agent runner sits behind one interface (`run_agent`), so our own runner and TinyFish are interchangeable.
6. **Honest by construction.** Observed-only language, null = N/A, mock/saved flags, no scoring of unverified data.
7. **A human approves anything that moves money or touches accounts.**
8. **Measure before claiming.** Any speed, cost or accuracy claim in the pitch must come from a measured number (§10.2b).

---

## 6. Features — what, why we chose it, how it works

Each feature uses the same template: **What · Why chosen · How it works · Depends on · Risks & guardrails · Build notes · Done when**.

---

### F1 — Same-hotel matching and like-for-like comparison (THE FACE) — EXISTS / PARTIAL

**What.** Group listings from different platforms that are the same property, then compare their *true payable* prices only when the rooms are actually comparable.

**Why chosen.** This is the original reason the project exists: users waste time hunting prices across sites. It is the visible value, the demo moment, and the thing a user would pay (or a platform would sponsor) for. Without correct matching and fair comparison, a verified price is just a number.

**How it works.**
- Normalise names; blend name, area/address, phone and geo similarity (§4.9); thresholds merged/suggested/separate; a human-readable `why` string ("Name 94%, same area, phone match").
- Comparable key per offer: guests/occupancy, nights, meal plan (normalised), cancellation category.
- Offers that differ from the majority get a plain-English non-comparable warning; they are shown but never silently compared.
- Suggested (0.75–0.89) matches are shown as "possible match" and excluded from pricing until confirmed.

**Depends on.** Discovery listings (live discovery is still unproven).

**Risks & guardrails.**
- Coverage: a hotel must exist on ≥ 2 platforms to compare — the weakest point; mitigate by adding platforms and by caching coverage.
- False merges are worse than missed merges: keep the conservative thresholds; add a "confirm same hotel" UI for suggested matches later.
- Never convert currencies; never compare different rooms.

**Build notes.** Add a labelled test set of real listing pairs from live discovery (positives, hard negatives like "Urban Nest Inn" vs "Urban Nest Inn & Suites") and tune only against that set. Add address/geo from live listings as soon as discovery runs live.

**Done when.** For a real search in two cities, ≥ 80% of true duplicates are merged, zero false merges in the labelled set, and every displayed comparison is like-for-like or flagged.

---

### F2 — Verdict, proof and handoff — EXISTS / PARTIAL

**What.** Turn the comparison into a decision ("book here"), show proof on demand, and hand the user to the winning site with everything needed to book the exact same room.

**Why chosen.** The user does not want a table; they want an answer. Proof is what makes the answer believable. Handoff closes the loop and is where affiliate or outcome revenue attaches.

**How it works.**
- Verdicts: cheapest verified, safest cheapest (free cancellation), best for you (weighted ranking by deal mode).
- "Show proof": price trail (listing → room → traveller → payment), fee lines tagged by kind (tax / platform fee / property fee / add-on), evidence links, "observed on this run" labels, add-ons and urgency messages.
- Handoff pack: **selection card** (hotel, room type, meal plan, cancellation, dates, guests, expected final payable, currency, verified-at), deep link + QR to the platform, disclaimer "Price verified at <time>. Re-check before paying; prices can change."
- Deep links may **not** restore the agent's cart, so the selection card must say what to pick and which price to expect.

**Depends on.** F1, F6 (proof), F5 (re-check).

**Risks & guardrails.**
- Never present a verdict from unverified offers; if fewer than two verified offers exist, say so plainly instead of inventing a winner.
- Taxes are not "hidden fees"; the UI and any draft message must keep them separate.
- The handoff's `copy_paste` details are demo placeholders; the real product lets the user supply their own and never stores card data.

**Build notes.** Frontend must use `offer.currency` (not a hardcoded ₹), handle null/empty states (ratings, listings, history), open agent tiles on `agent_started`, show a freshness chip on every price, and make blocked/unverified states look deliberate (§3.3).

**Done when.** A new user can go from search to the correct booking page with the right room in under two minutes, and can open proof for any price shown.

---

### F3 — Price database, cache and scheduler — PLANNED (highest-leverage engine feature)

**What.** A shared store of verified all-in prices keyed by property, platform and stay parameters, with freshness metadata, refreshed by a scheduler for popular hotels/dates and on demand.

**Why chosen.** This is the fix for unit economics. A live 3-platform comparison costs about ₹100–120 (estimate) but affiliate income at a 10% conversion rate is about ₹50 per comparison (§10). If one verification serves many users, cost per comparison falls toward zero while value stays. It also turns the product into a **data asset** (the moat) and makes answers instant instead of 3–6 minutes.

**How it works.**
- **Key:** `(hotel_id, platform, check_in, check_out, guests, rooms, currency, room_class/policy signature)`.
- **Record:** price shown, price payable, fee lines with kinds, cancellation category, meal plan, occupancy, evidence refs, `captured_at`, `source` (own agent / TinyFish / crowd), `confidence`.
- **Freshness (TTL) policy:** shorter TTL for near-term dates and volatile hotels, longer for far dates; the UI always shows "verified N minutes ago". Price older than TTL triggers a refresh in the background and a re-check at handoff.
- **Scheduler:** prioritise by demand (search frequency), proximity of dates, and hotels that appear on ≥ 2 platforms; spend budget on the top-N hot keys.
- **Price history:** append-only; powers F7 alerts and trend charts.
- **Storage:** start with SQLite/Postgres-compatible schema; on Google Cloud move to Cloud SQL or Firestore with Cloud Scheduler/Cloud Tasks driving refreshes.

**Depends on.** F4/F5 to produce data; F6 to attach proof.

**Risks & guardrails.**
- Stale data presented as fresh → mandatory freshness stamp + re-check before payment.
- Cache poisoning (especially with crowd data, F9) → source trust scores, outlier detection, signed observations.
- Only real observations enter history (mock/fake excluded or flagged `mock: true`).

**Build notes.** Define the schema and TTL rules first, then the "cache read → stale refresh" path, then the scheduler. Track **cache hit rate**, **cost per answered search**, **median answer time**, and the **moat metric** (§10.6).

**Done when.** A repeated search for a cached hotel returns in seconds with a freshness stamp, and measured cost per answered search is far below the live-run cost.

---

### F4 — Our own hybrid agent (deterministic playbooks + LLM recovery) — PLANNED

**What.** Our own browser-automation runner that walks a checkout using **deterministic scripted steps per site (playbooks)** and uses an LLM only to recover from surprises and to read/verify pages.

**Why chosen.** Relying fully on TinyFish means: ~$0.4 per checkout (estimated), 3–6 minutes per run, no control over speed, anti-bot posture or observability. A pure LLM agent we write ourselves would not fix cost or speed (25+ model calls per run). A **hybrid** can plausibly bring a run to tens of seconds and near-zero LLM cost (**hypothesis, not measured**), because most steps are scripted. Running it ourselves also lets us watch runs live, debug, and scale parallelism with our own infrastructure.

**How it works.**
- **Runner:** Playwright (Chromium) in a controlled environment; one browser context per run; guest only; never pays, never logs in, never enters OTPs (§9).
- **Playbook per site:** ordered steps (open prefilled URL → select hotel → select room matching occupancy/policy → fill guest details with dummy values → advance to payment page), each with selectors, expected-state assertions and timeouts.
- **LLM roles (Gemini for the Google build):** (a) recover when an assertion fails (find the element, dismiss a popup), (b) extract structured fields from page text/screenshots (price lines, room name, guests, cancellation text), (c) verify the extracted values against page text before we accept them.
- **Output:** the same `ProbeResult` schema TinyFish returns today, so `verify_offer` and everything downstream is unchanged.
- **Interface:** `run_agent(...)` in `api/services/tinyfish.py` becomes a router: `own` → playbook runner, `tinyfish` → current SDK, with automatic fallback. Fake mode stays.
- **Parallelism:** N contexts in parallel; concurrency limited by IP reputation and per-site rate limits, not by code.
- **Observability:** live view of each run (screenshots/video per step), structured step log, replayable traces — these also feed F10.

**Depends on.** The existing contract and scoring (unchanged). Evidence format (F6).

**Risks & guardrails.**
- Sites change layouts → playbooks break; need health checks (scheduled canary runs), alerts and the LLM recovery path.
- Anti-bot: our own datacenter IPs may be blocked more than TinyFish's stealth browsers. Mitigate with realistic browser setups, polite pacing, and — long-term — partnerships/APIs and extension/crowd data (F9). **We do not build the product around evading captchas or anti-bot systems** (§7.2).
- Legal/ToS exposure of automated checkouts (§9.5).
- Prompt injection from page content (§9.3): page text is data, never instructions.

**Build notes.** Start with **Cleartrip** (the platform that already works). Keep TinyFish as fallback. Measure and publish per-run **seconds, LLM tokens, cost, success rate** vs TinyFish (fill the table in §10.2b). Add Agoda next, Booking.com last (hardest: USD, slow flow).

**Done when.** On Cleartrip the own runner verifies a hotel with a success rate comparable to TinyFish, at a fraction of the time and cost, with identical output shape and evidence.

---

### F5 — Tiered verification and live re-check — PARTIAL (re-check exists; tiering PLANNED)

**What.** A cost-aware ladder: cached/cheap scan first → agent only on the top candidates → a live re-check on the winner right before payment.

**Why chosen.** Most of the cost is the agent walk. Users mainly need the true price for the **top 1–2** candidates, and need **fresh** truth only at the moment of paying. Tiering keeps answers fast and cheap without lying about freshness.

**How it works.**
1. **Tier 0:** cache lookup (F3).
2. **Tier 1:** cheap listing scan (price shown, rating, availability) to shortlist.
3. **Tier 2:** checkout verification (F4/TinyFish) for the top 2 candidates per hotel×platform pair.
4. **Tier 3:** live re-check of the chosen offer using the captured hotel URL and the same room/meal/cancellation; observation-only message "Price moved INR A → INR B in N min (observed)"; feeds the stability component of transparency and price history.

**Depends on.** F3, F4.

**Risks & guardrails.**
- Re-check is a **spending endpoint**: budget guard, `DISABLE_LIVE` switch, max 2 re-checks per search (already implemented), and clear loading UI (3–5 min live).
- Never infer causes of price movement.

**Done when.** Median time to first useful answer < 10 s on cache hits and < 90 s on misses, with a re-check path that always runs before handoff for stale data.

---

### F6 — Signed evidence receipts — PLANNED (trust layer)

**What.** For every verified price, a tamper-evident "receipt": the captured values, page text, timestamps, step trail and (where possible) screenshots, hashed and signed, shareable as a proof link.

**Why chosen.** Our promise is "prove it". Today proof is a stream link (can expire) plus text snippets. Signed receipts make proof durable and portable, which unlocks refunds/disputes, B2B audits, regulator and consumer-group use, and cache trust (F3, F9).

**How it works.**
- **Receipt payload:** offer fields, fee lines with kinds, page-text snippets (listing/room/payment), screenshots when available (own runner can capture them; TinyFish SDK v0.11.0 cannot), run metadata (runner, version, duration), `captured_at` (+05:30).
- **Integrity:** canonical JSON → SHA-256 hash; chain hashes of per-step artifacts; sign with an Ed25519 key held in a secret manager; optional public verification endpoint and a printable report (already have an escaped HTML report).
- **Storage:** Cloud Storage bucket for artifacts; `/evidence` static route for the hackathon version (path traversal already blocked).
- **Language:** always "observed on this run"; no accusations; no claims about cause.
- **Minimum viable version for the buildathon:** SHA-256 hash of canonical JSON + page text, shown in the proof view; signing can follow.

**Depends on.** F4 for screenshots (otherwise page text only).

**Risks & guardrails.**
- Evidence must never contain PII or secrets (dummy guest details only).
- HTML-escape everything dynamic (page text comes from third-party sites).
- Don't oversell: a receipt proves what *our run observed at that time*, not what any user will be charged.

**Done when.** Any price shown in the UI can open a receipt whose hash verifies, whose page text contains the quoted amounts, and which still opens after the stream link expires.

---

### F7 — Price-drop watch and rebooking alerts — PLANNED (consumer hook)

**What.** After a user books a **refundable** room (or saves a hotel), we watch the true price and alert them when a better verified deal appears, with a one-tap path to rebook.

**Why chosen.** It gives users a reason to come back, produces recurring value, and generates the "money saved" events that outcome-based pricing (F8) needs. It also reuses the cache/scheduler (F3), receipts (F6) and re-check (F5).

**How it works.**
- User saves a hotel/dates (and optionally their booked price + cancellation deadline).
- Scheduler refreshes that key more often as the cancellation deadline approaches.
- If a verified price for a comparable, refundable room is lower by more than a threshold (after counting any cancellation risk), send an alert with proof and the handoff pack.
- **Alerts only.** The user decides, cancels the old booking and books the new one themselves; **the agent never books or cancels on the user's behalf.**

**Depends on.** F3, F5, F6.

**Risks & guardrails.**
- Only recommend rebooking when the old booking is genuinely free to cancel (we must know the policy and deadline from the user or evidence).
- Never claim guaranteed savings; show the verified-at time; re-check before acting.

**Priority note (v2).** First item on the buildathon cut list (§12.4): it is a retention feature, and the demo works without it.

**Done when.** A saved hotel triggers an alert with proof within the refresh window when a cheaper comparable room is verified.

---

### F8 — Outcome-based pricing ("we earn when you save") — PLANNED (business model)

**What.** Charge a share of money actually saved (or a small fee when a verified better option is accepted), instead of charging for searches.

**Why chosen.** It removes the "why would I pay for information?" objection, aligns incentives with the user, and matches our proof-first brand. It also fits the cache model: we are not selling a single verification (whose cost we amortise), we are selling savings. Affiliate commission on handoff remains the baseline consumer revenue.

**How it works.**
- **Savings definition (must be strict and auditable):** difference between the best verified comparable price and the user's reference price (their prior booking or the most expensive comparable verified price), backed by receipts.
- **Revenue paths:** affiliate commission via handoff links; a success fee for rebooking savings; subscriptions for frequent bookers/agents (F11).
- **Pricing options evaluated:** pay-per-insight (₹29–99) → rejected as the primary model because it conflicts with caching and punishes users when we fail; freemium "preview free, unlock proof/handoff" is a fallback; credit packs and subscriptions are secondary.
- **Rule:** **no charge for blocked or unverified results** — and say so on the pricing page, because it is a selling point.

**Depends on.** F7, F6.

**Risks & guardrails.**
- Attribution disputes → receipts and clear savings definitions.
- Affiliate programs may void automated/test bookings; our probes never complete bookings, but partner terms must be read before launch.
- No payment processing for the hackathon demo — use a mock "Unlock proof" button; real version uses UPI/Razorpay (never store card data).

**Done when.** The savings calculation is reproducible from receipts and a pilot cohort pays (or would pay) on a defined event.

---

### F9 — Browser extension and crowd observations — PLANNED (distribution + second data source; ranked up in v2)

**What.** A browser extension that shows the true all-in price on booking pages as the user browses, and — with explicit consent — contributes the observed checkout price to the shared database.

**Why chosen.** It is our best answer to "why would a user come to us?" (§1.2). It attacks three problems at once: (1) **distribution** — it meets users where they shop, so we do not need to win the search-habit battle; (2) **cost** — the user's own browser sees the payable price, so no agent run is needed; (3) **anti-bot** — a real user on a residential IP solves any captcha themselves. This is the "Keepa/Honey model" applied to travel (used as an analogy only). Each user makes the database better for everyone, so the moat grows with usage instead of with our spend.

**How it works.**
- Reads only the price-related elements on supported checkout pages; sends `(hotel, platform, stay params, price lines, currency, timestamp, page-text snippet hash)`.
- Shows the user our verified prices for the same hotel on other sites, in-page.
- **Data minimisation:** never reads passwords, payment fields, OTPs, or personal details; no browsing history outside supported domains; clear consent and an off switch.
- **Trust:** observations are signed by the extension, weighted by contributor reputation, and cross-checked against agent captures; outliers are quarantined (cache-poisoning defence).

**Depends on.** F3 (store), F6 (format).

**Risks & guardrails.**
- Privacy/regulatory exposure → strict minimisation, consent, transparent policy.
- Store-review and per-site DOM breakage → keep it small, one site first.
- Crowd data can be wrong or malicious → trust scoring, quorum, never mark crowd-only prices "verified" without agent confirmation unless policy says so.

**Done when.** On one supported site, the extension displays our cross-site comparison and contributes consented observations that raise cache coverage without extra agent spend.

---

### F10 — Self-writing playbooks — PLANNED (scales F4 to new sites)

**What.** An LLM watches one successful guided run on a new site (steps, DOM states, outcomes), then **compiles it into a deterministic playbook** that later runs replay cheaply.

**Why chosen.** Writing and maintaining playbooks by hand does not scale to many sites or layout changes. If new-site cost is "one expensive run, then cheap forever", adding platforms (and verticals, F13) becomes a minutes-scale task. It is also our strongest **technical/Google-AI story** (Gemini does the learning and repair step).

**How it works.**
1. **Explore:** an LLM-driven run completes the checkout once, logging each action, target element (multiple selector strategies) and the expected page state after it.
2. **Compile:** convert the trace to a playbook DSL with assertions; parameterise hotel/dates/guests.
3. **Validate:** replay N times on varied inputs; accept only if outputs match expected shapes and reconcile.
4. **Repair:** when an assertion fails in production, the LLM proposes a patch; the patch must pass validation before replacing the playbook; alerts go to a human.
5. **Canary:** scheduled health runs per site.

**Depends on.** F4 runner and trace format.

**Risks & guardrails.** Overfitting to one session (validate on varied inputs); runaway repair loops (human approval for playbook changes; **no automatic retry loops around agents**).

**Done when.** A new site's playbook is generated from one guided run and passes validation with no hand editing.

---

### F11 — B2B and regulation angle — PLANNED (first paying customers; ranked up in v2)

**What.** Sell verified all-in prices, evidence receipts and fee data to businesses and watchdogs: travel agents, corporate travel desks, event planners, comparison sites, consumer groups, journalists, and regulators.

**Why chosen.** The consumer loop loses money per comparison unless the cache works (§10.2). Businesses book often and in bulk, value time and proof, and can pay a subscription independent of conversion — one customer covers many verifications and makes cache economics work. Regulators and consumer groups care about drip pricing; observed-fee evidence is relevant to them (**regulatory references must be verified before use, §16b**).

**How it works.** Team accounts, exportable reports (we already generate a printable evidence report), bulk quote API, fee-trend dashboards, and dispute-ready receipts (F6). Sell data as "observed on this run" — never as accusations.

**First segment (decide in §13.1).** One of: independent travel agents, corporate travel desks, event planners. Pick one based on interview results; do not build for all three.

**Risks & guardrails.** Legal review before targeting regulators/journalists; no claims of intent ("dishonest", "scam"); data licensing terms.

**Done when.** At least 3 travel-agent/corporate users validate willingness to pay, and one pilot runs on bulk quotes.

---

### F12 — Verified-price API for AI agents — ROADMAP

**What.** `verified_price(hotel, dates, guests, currency)` → price, fee lines, cancellation category, evidence refs, `captured_at`, confidence; consumed by travel assistants and booking bots.

**Why chosen.** Assistants that book on behalf of users need a trustworthy all-in price before they act. Infrastructure revenue scales with usage and does not require a consumer app. **This is a thesis, not a proven market** — pitch it as direction.

**Depends on.** F3 (data), F6 (proof). Do not build before those are solid.

**Risks & guardrails.** Rate limits, abuse, licensing terms, accuracy SLAs, and clear freshness semantics.

---

### F13 — Vertical expansion — ROADMAP

**What.** Apply the same engine to other drip-priced checkouts: flights (baggage, seats, convenience fees), event tickets, food-delivery fees, cabs, subscriptions.

**Why chosen.** The core capability — "walk a checkout, prove the final price, compare like for like" — is general. Hotels are the wedge because we have working probes and clear comparability; other verticals broaden the market once the engine and playbook tooling (F10) are cheap.

**Risks & guardrails.** Each vertical has its own comparability definition and ToS landscape; expand one at a time, only after hotels have paying users.

---

### F14 — Card/fintech and platform partnerships — ROADMAP

**What.** Show "verified all-in price" inside payment or banking flows (cards, UPI apps, rewards programs) and partner with platforms for API/affiliate access.

**Why chosen.** Distribution at the point of payment and legitimate data access reduce both anti-bot risk and acquisition cost. Needs real relationships, so it is a roadmap item, not a build item.

---

## 7. Ideas we considered and dropped (or folded in) — and why

### 7.1 "Use real user details and logged-in accounts instead of a guest" — DROPPED for the core product

The thinking was: use real details so the agent can go further, and log in via Google to avoid captchas. We rejected it as a core strategy because:

- **It breaks our trust promise.** The strongest line in the pitch is "we never touch your account or pay". A logged-in agent changes that.
- **Security.** An agent inside a user's account or Google session is exposed to hostile page content (prompt injection) that could try to make it act (navigate, change settings, expose data). The blast radius is the user's real account.
- **It increases ToS and ban risk** for the user's real accounts, not just for a throwaway guest session.
- **It does not remove the hard parts.** After login, sites can still add OTP or captcha, and real bookings involve real money and liability.
- **Evidence is cleaner as a guest.** A guest probe cleanly shows "what a new visitor is quoted".

**What we keep from the idea (the legitimate value):** logged-in/member prices matter. The safe way to capture them is the **browser extension (F9)** with the **user present**, reading only price elements on their own session with consent, never automating their login.

### 7.2 "Use Google login to bypass captchas" — DROPPED as a strategy

- Google blocks sign-in from automation-controlled browsers, so this is unreliable.
- Sites can still demand OTP or captcha after login.
- Building the product around defeating anti-bot protections is a legal, ethical and business risk (and a bad answer to a judge's first question).
- **Our stance:** when a platform blocks us, we show it honestly as `blocked` with a reason. We reduce blocking through legitimate means — polite pacing, realistic browsers, crowd/extension data where the user is present, and long-term **partnerships/APIs** — not circumvention.

### 7.3 "A pure LLM agent that we write ourselves" — REJECTED in favour of hybrid (F4)

A fully LLM-driven agent still needs ~25 model calls per checkout, so it would not fix cost or speed and would still be flaky. The hybrid keeps the LLM only where it adds value (recovery, extraction, verification).

### 7.3b "Run agents on our own machine so we can watch them" — KEPT (as part of F4)

Valuable for debugging, observability and trace capture (feeds F10). Note it means we own anti-bot posture and infrastructure that TinyFish currently provides.

### 7.4 "Many agents in parallel to cut wait time" — FOLDED IN (not a feature)

Parallelism is a property of the runner. The real limits are per-site rate limits and IP reputation, plus cost. It reduces wall-clock time but not cost per verification; caching (F3) is what removes both.

### 7.5 "Charge per insight" — FOLDED into F8 as a fallback

Pay-per-insight conflicts with the cache model (one verification serves many) and charges users when results are poor. We keep it only as a secondary/freemium path ("preview free, unlock proof/handoff"). Rule retained: never charge for blocked/unverified results.

### 7.6 "Single-site mode (verify one platform only)" — LIMITED USE

Useful as a **demo fallback** (Cleartrip works live) to show listed-vs-final price. It is **not** the product: without ≥ 2 platforms there is no comparison. Any single-platform output must make no cross-platform claim.

### 7.7 "Lead with consumer affiliate revenue" — DEMOTED in v2

The unit economics (§10.2) show the consumer affiliate loop loses money per comparison unless cache hit rate is high. Consumers remain the free funnel and the extension's user base; **B2B subscriptions lead the revenue story**.

---

## 8. Ranking and dependency graph

### 8.1 Ranking (what to build first, by contribution to a complete product) — updated in v2

| Rank | Feature | Layer | Why it ranks here | When |
|---|---|---|---|---|
| 1 | **Evidence dataset (§2.4)** | Proof | Turns an anecdote into a statistic; cheapest credibility win | Now (today) |
| 2 | **F1 Same-hotel matching + comparison** | Face | It is the visible product | Now (harden) |
| 3 | **F2 Verdict, proof, handoff** | Face | Converts the comparison into a decision and a booking | Now (harden) |
| 4 | **F3 Price database + cache + scheduler** | Engine | Fixes unit economics, speed, creates the moat | Now |
| 5 | **F4 Own hybrid agent** | Engine | Cheap/fast capture that feeds F3 | Now |
| 6 | **F5 Tiered verification + re-check** | Engine | Keeps cost low without lying about freshness | Now |
| 7 | **F6 Signed evidence receipts** | Engine/trust | Makes data believable and sellable | Now (hash first) |
| 8 | **F9 Extension + crowd data** | Growth/data | Distribution answer + free data; needs F3 + F6 | Next (ranked up from 9) |
| 9 | **F11 B2B + regulation** | Money | First paying customers; leads revenue story | Next (ranked up from 11) |
| 10 | **F7 Price-drop watch/alerts** | Growth | Retention hook; needs F3 + F6 | Next |
| 11 | **F8 Outcome-based pricing** | Money | Business model; needs F7 + F6 | Next |
| 12 | **F10 Self-writing playbooks** | Engine | Scales F4 to new sites; Google-AI story | Next |
| 13 | **F12 AI-agent API** | Money | Infrastructure play after F3/F6 | Roadmap |
| 14 | **F13 Vertical expansion** | Growth | After the hotel wedge works | Roadmap |
| 15 | **F14 Fintech/platform partnerships** | Growth | Needs relationships | Roadmap |

### 8.2 Dependencies

```
F1 -> F2
F3 <- F4, F5 (data in)          F3 -> F1 (instant answers), F7, F12
F4 -> F10 (traces)              F6 -> F2, F3, F8, F9, F11, F12
F7 -> F8                        F9 -> F3
F11 needs F6 + F3               F12 needs F3 + F6
```

### 8.3 Why this makes a *product* and not a pile of ideas

Every item sits in one loop: **capture** (F4, F9, TinyFish fallback) → **store and serve** (F3) → **prove** (F6) → **compare and decide** (F1, F2, F5) → **keep users and earn** (F11, F7, F8). Items that did not fit the loop were dropped (§7).

---

## 9. Non-negotiable rules (safety, honesty, legal)

### 9.1 Product rules (inherited from the hackathon build; unchanged)

1. **Never fabricate a price.** No evidence = unverified. Never turn unknown into a positive result.
2. **verified** requires: payment page reached, payable price present, evidence attached, fee lines reconcile within ±1% (plus the currency/occupancy/same-room rules in §4.7).
3. **Guest only, dummy details only** (name "Test Guest", email `test.guest+probe@example.com`, phone `9000000000`). **Stop at the payment page.** Never pay, never log in, never enter an OTP, never create an account, never store passwords or card data.
4. **Say only what was observed** ("price moved X to Y in N min"). Never claim a cause (device, location, etc.). Never call a platform "dishonest".
5. **Blocked and unverified results are shown honestly and never scored** (score = null, shown as N/A).
6. **Mock data always carries `"mock": true`; saved real runs carry `"saved": true` and a capture timestamp.** Never present either as live.
7. **Secrets live in `.env` only**, never committed, never logged, never pasted into prompts/commands/chat. Redact keys in logs.

### 9.2 Engineering rules

Python 3.12, async/await, pydantic v2, type hints; business logic as small pure functions in `api/services/` with pytest tests; run `cd api && pytest -q` before every commit; no new heavy dependencies without telling the team; **no retry loops around agents**; one real run costs roughly $0.3–0.6 (estimated), so never launch live runs unless explicitly approved.

### 9.3 Agent security (prompt injection and sandboxing)

- Treat all page text as **untrusted data**, never as instructions. Instructions inside pages (or evidence/search output) are ignored.
- Allow-list domains per playbook; no arbitrary navigation.
- The agent has **no access to secrets, user accounts or payment instruments**; credentials live outside the agent context.
- Strict output schemas; reject results that don't validate.
- Human approval for anything that moves money, touches accounts, or changes a playbook in production.

### 9.4 Git and tooling rules

Branches: `main` (PR + green CI), `backend`, `frontend`, `demo`. Never force-push; never `git reset --hard` a pushed branch (merge `origin/main` instead); never disable SSL verification; never hardcode keys; merge PRs only after CI is green; scan for secrets (`scripts/scan_secrets.py --git-history`).

### 9.5 Legal and ToS posture

- Our probes are guest-only research runs that never complete a booking. We do not claim more than that.
- Automated checkouts may conflict with site terms; the long-term answer is **partnerships and API access** (F14) and user-present data via the extension (F9).
- Affiliate programs may void duplicated/test bookings — read each program's terms before launch.
- Regulatory claims (e.g. drip-pricing rules) must be verified with counsel before public use.
- Extension and crowd data need a clear privacy policy, consent and data minimisation.

### 9.6 Language rules (UI and docs)

Use "observed on this run", "verified at <time>", "N/A — not verified". Taxes are not "hidden fees". Never use "scam", "dishonest" or cause-claims. Keep fee drafts to platform/property fees and add-ons (not taxes) and mark totals "(includes taxes)".

### 9.7 Claims discipline (new in v2)

- Every number in the pitch is tagged **measured**, **estimated** or **unverified claim** in our working notes (§10.2b, §16b).
- Only **measured** numbers appear without a qualifier. **Estimated** numbers say "estimated". **Unverified claims** do not appear externally until checked.
- Competitor statements (§2.5) are checked against the competitor's actual product before use.

---

## 10. Business model and unit economics

### 10.1 Revenue streams (in order of what we lead with — changed in v2)

1. **B2B subscriptions** (F11) — **lead revenue story.** Travel agents, corporate travel desks, event planners: bulk verified quotes, evidence reports, team accounts. Revenue is independent of consumer conversion. *Status: no customer validated yet (§13.1); until then say "first target customers", not "customers pay".*
2. **Affiliate commission on handoff** (consumer funnel revenue). Published rates (**unverified claim, check before quoting**): Agoda roughly 4–7% of booking value; Booking.com roughly 4% through affiliate networks. Cleartrip and other Indian programs were **not verified**. Agoda's program is reported to track and remove duplicated/fake/test bookings.
3. **Outcome-based fees** (F8): a share of verified savings, rebooking success fees.
4. **Data and receipts** (F11): fee data/price history for consumer groups, journalists, comparison sites — sold only as "observed on this run".
5. **AI-agent API** (F12): usage-based pricing for assistants that need verified prices (thesis, not proven).
6. **Premium for consumers:** price-drop alerts, history, proof exports.

### 10.2 Unit economics — why caching is mandatory

All figures are **estimates**; replace them with measured numbers (TinyFish dashboard + our own metrics).

- Cost per live checkout: **~23–30 steps × ~$0.016 ≈ $0.37–0.48**; roughly ₹30–40 per run at current exchange rates (approximation).
- A live 3-platform comparison ≈ **₹100–120**.
- Affiliate income: 5% on a ₹10,000 booking ≈ **₹500** (rate is an unverified claim).
- At a 10% comparison→booking conversion, income per comparison ≈ **₹50** → **below cost** (loss) if every user triggers fresh runs.

**Levers that flip it:**
1. **Cache (F3):** one verification serves many users; cost per answered search trends to near zero.
2. **Own hybrid agent (F4):** lower cost and time per capture.
3. **Tiering (F5):** agent only on the top 2 candidates; live re-check only at handoff.
4. **Crowd data (F9):** observations at zero agent cost.
5. **B2B (F11):** subscription revenue independent of conversion.
6. **Outcome pricing (F8):** aligns revenue to measurable savings.

### 10.2b Measured vs estimated (new in v2) — keep this table current

| Metric | Value today | Label | How to measure / replace |
|---|---|---|---|
| Observed gap, La Marvella on Cleartrip (gate run) | +34.6% (₹8,867 → ₹11,933) | **Measured** (n = 1) | Replace with evidence-dataset median (§2.4) |
| Cleartrip verified live | Yes | **Measured** | Keep run ids in `results/` |
| Agoda run 2 payable | ₹12,936.93, +18.2% | **Unverified** until evidence re-checked | §16b item 2 |
| Booking.com | Unresolved | **Measured** (timeout, USD) | Confirm attempt 3 outcome |
| TinyFish seconds per checkout | 180–360 s | **Measured** (timeout cap 360 s) | Log per-run durations |
| TinyFish cost per checkout | $0.37–0.48 | **Estimated** (steps × 0.016) | Read TinyFish dashboard |
| Own hybrid agent seconds / cost / success | — | **Not measured** | Benchmark one Cleartrip run vs TinyFish |
| Cache hit rate / cost per answered search | — | **Not measured** | Instrument F3 |
| Affiliate rates (Agoda, Booking.com) | 4–7% / ~4% | **Unverified claim** | Read each program's terms |
| Comparison→booking conversion | 10% | **Assumed** | Replace with handoff click-through data |

### 10.3 Metrics we must track from day one

Cost per verified price; cost per answered search; cache hit rate; median time to first answer; verified rate per platform; % of comparisons with a leak ≥ 10%; handoff click-through; affiliate conversion; re-check price-move rate; cost per platform per week (maintenance); **moat metric (§10.6)**.

### 10.4 Pitch-safe statements

- "Travel businesses that need trustworthy all-in quotes are our first paying customers; travellers use TinyTravel free." (Change to "first target customers" until §13.1 has a validated customer.)
- "We're profitable once one verification serves many users."
- Do **not** promise specific revenue or prize figures; present the model and unit economics instead.

### 10.5 Pricing sketch for the first B2B segment (to test in interviews, not decided)

| Tier | For | Rough shape (hypothesis) |
|---|---|---|
| Free | Travellers, extension users | Cached verified prices with freshness stamp |
| Pro / team | Agents, desks | Fresh verification on demand, bulk quote export, evidence reports, team seats |
| Data / API | Comparison sites, consumer groups, AI assistants | Usage-based access to verified prices and receipts |

Price points are deliberately **not** set here; they come from the interviews in §13.1.

### 10.6 The moat metric (new in v2)

**Primary metric: number of fresh, verified hotel × platform × stay-date keys in the price database**, tracked weekly, plus:

- **Coverage:** share of searched hotels that exist on ≥ 2 platforms with a fresh verified price.
- **Cost trend:** cost per verified key (should fall as F4 and F9 come online).
- **Source mix:** share of observations from own agent vs TinyFish vs crowd (crowd share rising = flywheel working).

This is the number that shows the data asset compounding. Everything in the pitch about "the moat" should point to it.

---

## 11. Google AI and Google Cloud plan (for the Startup Buildathon)

The buildathon scores **use of Google AI** (and requires an AI-powered product built with Google AI/Cloud). Currently we use Anthropic for intake and TinyFish for agents; the startup build should move the AI core onto Google.

| Need | Google component (verify current availability/names at build time) |
|---|---|
| Intake (free text → structured request) | Gemini |
| Page understanding / extraction (text + vision) | Gemini (multimodal) |
| Fee label classification, verdict explanations | Gemini |
| Playbook generation and repair (F10) | Gemini |
| Dev workflow | Google Antigravity, AI Studio, Agent Skills |
| Hosting API/workers | Cloud Run |
| Scheduler | Cloud Scheduler / Cloud Tasks |
| Database | Cloud SQL or Firestore |
| Evidence artifacts | Cloud Storage |
| Secrets/signing keys | Secret Manager |
| Observability | Cloud Logging/Monitoring |

Notes: check whether Gemini offers a computer-use/agent capability at build time before promising it in the pitch; keep model names in config (env), never hardcoded; keep TinyFish behind the interface as fallback.

---

## 12. Startup Buildathon India 2026 — facts, plan, demo

### 12.1 Facts (from startupbuildathon.com, checked 10 Nov 2026 — re-check dates before relying on them)

- Organised via Hack2skill with Google AI/Google Cloud (powered with nasscom and HeadStart).
- **Applications close 13 Nov (today, per this version's date)**; selected teams hear by **18 Nov**. Application = idea, solution, architecture, pitch deck.
- **City buildathons 20–21 Nov** in 10 cities (Ahmedabad, Bengaluru, Chennai, Delhi, Hyderabad, Jaipur, Kochi, Kolkata, Mumbai, Pune): day 1 ideate/design with mentors; day 2 build, submit, present to the jury.
- **Regional showcases:** 23 Nov Gurugram, 25 Nov Mumbai, 27 Nov Hyderabad. **Grand finale: 2 Dec, Google Bengaluru.**
- **Prize:** top 10 teams share USD 100,000 (USD 10,000 per team: USD 5,000 cash + USD 5,000 Google AI & Cloud credits), subject to terms/taxes. Plus mentors, VCs, startup programs.
- **Eligibility:** early-stage startups or aspiring entrepreneurs, solo or 2+ people, **must be building an AI-powered solution**.
- **Judging criteria:** founder profile; product potential; market viability; technical architecture; use of Google AI.
- **Action:** confirm all four teammates are available 20–21 Nov and pick one city (Bengaluru is the natural choice).

### 12.2 How our plan maps to the criteria

| Criterion | Our answer | Weakest point (v2) |
|---|---|---|
| Founder profile | Built a working, evidence-based prototype in a day at the TinyFish hackathon; real data; students with AI-search/agent experience; clear why-we-built-this story. | Add the evidence dataset (§2.4) so the story rests on more than one run. |
| Product potential | Clear, relatable pain; a demo that shows the answer; comparison + proof + handoff. | Answer "why would users come to us" with the extension (§1.2). |
| Market viability | Hotel booking is huge and drip pricing is a known pain; revenue via B2B, outcome pricing, affiliate, API; **cache-driven unit economics**. | **Softest criterion.** Needs customer interviews (§13.1) and a competitor table (§2.5). |
| Technical architecture | Contract-first backend, pure-function scoring with golden tests, hybrid agent, cache, signed receipts, tiered verification, guardrails. | Own-agent numbers are not yet measured (§10.2b). |
| Use of Google AI | Gemini for intake, extraction, classification, explanations and playbook learning; Cloud Run/Scheduler/SQL/Storage/Secret Manager. | Confirm Gemini model names and capabilities at build time. |

### 12.3 What to submit by 13 Nov (trimmed in v2)

1. **One-page idea and problem** — use §1 (with the v2 positioning), §2.2 and, once filled in, the §2.4 headline sentence.
2. **Architecture diagram** — use §5; mark Gemini and Google Cloud components.
3. **Pitch deck** — lead with the problem and the proof, then the comparison, then the cache as the 10x story. Core slides: problem, evidence, solution, demo, architecture, business model (B2B first), competition (§2.5), roadmap. **Features F1–F6 on the main slides; F7–F14 on one roadmap slide.**
4. **2-minute demo video** from the real saved run (do not rely on a live run for the video).
5. **Google AI usage plan** — use §11.

**Pre-submission checklist**

- [ ] Evidence dataset headline sentence filled with real numbers (or the +34.6% shown as "largest observed case, n = 1").
- [ ] Positioning uses "verified all-in price layer".
- [ ] Extension named as the distribution answer.
- [ ] No unverified claim (§16b) appears externally.
- [ ] Customer validation line is true as written (or says interviews are scheduled, with dates).
- [ ] Competitor table claims checked against actual products.

### 12.4 Scope for the 2-day city buildathon (20–21 Nov)

**Must ship (the loop):**
- Cleartrip run through our **own hybrid agent** (playbook + Gemini recovery/extraction) behind `run_agent`, TinyFish as fallback; measured seconds/cost/success vs TinyFish (fill §10.2b).
- **Price cache + freshness stamp**: same hotel returns instantly the second time.
- **Comparison UI** across at least 2 platforms for one hotel (own agent for Cleartrip + saved/real offers or TinyFish for Agoda), listed vs final, best option highlighted.
- **Receipt with proof view** (page text + hash; signing if time allows).
- Gemini in the loop (intake + extraction + explanation) and the API hosted on Cloud Run.

**Nice to have:** price-drop watch on a saved hotel (alert only).

**Show only as roadmap slides:** outcome pricing, extension/crowd data (show a mock of the in-page comparison if useful), self-writing playbooks, B2B/regulation, AI-agent API, verticals, partnerships.

**Cut list (in order) if time runs short:** price-drop watch → receipt signing (keep hash + page text proof) → second platform live (use saved offers) → Cloud Run (demo locally) → own agent (fall back to TinyFish and present the architecture).

### 12.5 Suggested team split (four people)

| Role | Owns |
|---|---|
| **A — Agent** | Playwright runner, Cleartrip playbook, Gemini recovery/extraction, `run_agent` router, benchmarks vs TinyFish |
| **B — Data** | Price DB schema, cache read/refresh path, scheduler, price history, receipts (hash/sign) |
| **C — Distribution/Trust** | Evidence dataset, customer interviews support, extension mock/prototype (if time) or evidence/receipt UI, Cloud Run/Secret Manager setup |
| **D — Product/Frontend/Pitch** | Comparison UI, verdict/proof/handoff screens, Gemini intake, deck, video, customer interviews |

Suggested continuity: existing backend owner continues on A/B; existing frontend owner on D. Assign names in the team channel and update this table.

### 12.6 Demo script (3 minutes)

1. **Hook (15 s):** "The price you see isn't the price you pay." Real example: ₹8,867 → ₹11,933 (+34.6%) on Cleartrip, followed by the dataset median if available.
2. **Problem (20 s):** Final price only appears at the end of checkout; five sites, different rooms, different fees.
3. **Solution (30 s):** We verify the same hotel across sites as a guest (never paying), prove the payable price, and compare like for like.
4. **Live moment (60 s):** Start a run a few minutes earlier; narrate while tiles run; then repeat the search → **instant from cache** with a freshness stamp ("verified N min ago"). This is the cost/speed story.
5. **Verdict (30 s):** side-by-side listed vs final; best verified option; taxes shown separately from fees; "Show proof" (page text + receipt hash).
6. **Honesty (20 s):** blocked/unverified are shown as N/A (e.g. a platform returned USD → flagged, never converted).
7. **Handoff (15 s):** selection card + QR to the winning site; re-check before paying.
8. **Close (10 s):** extension for distribution, B2B for revenue, API for AI agents; "stop checking five sites."

**Rules for the demo:** say only what is in the saved/verified data; keep a recorded real run one click away as safety net (record it now, §4.2); keep `DISABLE_LIVE=1` on any public deployment until you go on stage; check the hosted key's balance beforehand; start live runs ≥ 5 minutes before presenting.

### 12.7 Likely judge questions

- **Do you pay / complete bookings?** No. Guest-only, dummy details, stop at the payment page.
- **Why not scrape?** The payable price only exists after interacting through checkout.
- **How do you avoid hallucinated prices?** Strict schemas, deterministic math, evidence required, "unverified" when unsure, golden tests.
- **What if sites block you?** We show `blocked` honestly; we reduce blocking via partnerships/APIs and user-present extension data, not circumvention.
- **Is it legal/ToS-safe?** Guest-only research that never completes a booking; long-term path is partnerships and APIs; legal review before regulator/journalist use.
- **Cost per run and business model?** ~$0.4 per live checkout today (estimated); the cache and own agent are meant to make the marginal cost near zero (to be measured); revenue via B2B subscriptions first, then savings-based fees, affiliate and API.
- **Why would users come to you instead of Google Hotels or an OTA?** We show the verified post-checkout price with proof, and the extension meets users inside the booking page; businesses pay for time saved and receipts.
- **Is the gap typical or a one-off?** Answer with the §2.4 dataset (N, median, range). If not done, say plainly that the +34.6% is the largest observed case, n = 1.
- **What's the moat?** The verified-price database (the moat metric, §10.6), signed evidence, playbook library and crowd data flywheel.
- **Who is your first customer?** The segment chosen in §13.1; state the interview count honestly.

---

## 13. Validation plan and success metrics

### 13.1 Customer discovery (dated deliverable — one validated customer beats ten ideas)

**Target this week:** 3–5 conversations with **one chosen segment** first (independent travel agents recommended as the easiest to reach; confirm by interviews), then widen.

Ask:
- How many hotel quotes per week? How much time per quote?
- How do they compare all-in prices today? What breaks?
- What would they pay (per month or per quote) for verified all-in quotes with proof? Who else pays for something similar?
- How do they handle cancellations and price drops?
- Would they use an extension? Would they want an API or export?

Also ask 5–10 students/families: do they compare sites, how long, what fees surprise them, would they use an extension.

**Log (keep in `docs/INTERVIEWS.md`, one entry per conversation):** date, segment, size of business, quotes per week, time per quote, willingness to pay (exact words), preferred channel (web, extension, API), top objections.

**Decision to make after 3–5 interviews:** the first B2B segment (§16 item 10) and the first pricing hypothesis (§10.5).

### 13.2 Technical success criteria

| Metric | Target for the buildathon build |
|---|---|
| Own agent verified rate on Cleartrip | ≥ TinyFish's (document both) |
| Median seconds per verified checkout | far below the 180–360 s of TinyFish (document measured numbers) |
| Cost per verified checkout | far below ~$0.4 (document measured numbers) |
| Cache hit answer time | seconds |
| Receipt integrity | hash verifies; page text contains quoted amounts |
| Contract/tests | `pytest` green; fixtures validate; secrets scan clean |

### 13.3 Product success criteria

- A user can go from search to the right booking page with the correct room in < 2 minutes.
- Every price shown opens proof.
- No unverified price is ever scored or ranked.

### 13.4 Business validation criteria (new in v2)

- Evidence dataset: N ≥ 12 reconciled checkouts with a stated median.
- ≥ 3 interviews logged in the chosen B2B segment; ≥ 1 with a stated willingness to pay.
- Moat metric tracked weekly from the first cached run.

---

## 14. Risk register

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | Anti-bot blocking on our own infra | Runs fail | Hybrid agent + TinyFish fallback; polite pacing; crowd/extension data; partnerships; honest `blocked` status |
| R2 | Sites change layouts | Playbooks break | Canary runs, LLM recovery, validated playbook repair (F10) |
| R3 | ToS/legal exposure | Cease-and-desist, loss of access | Guest-only, never complete bookings, partnerships/APIs, legal review |
| R4 | Stale cached prices | Wrong decisions | TTL policy, freshness stamp, mandatory re-check before handoff |
| R5 | Unit economics don't close | No business | Cache-first design, own agent, tiering, B2B, outcome pricing; track metrics from day one |
| R6 | Prompt injection / agent security | Data or account compromise | Page text = data; allow-listed domains; no secrets/accounts in agent context; schema validation |
| R7 | Crowd data poisoning | Wrong prices | Signed observations, reputation, outlier quarantine, agent cross-check |
| R8 | Privacy (extension) | Regulatory/reputation damage | Data minimisation, consent, clear policy, off switch |
| R9 | Coverage (hotel on < 2 platforms) | No comparison | More platforms, coverage cache, clear UI message |
| R10 | Platform currency/room differences (USD, occupancy) | Wrong comparisons | Currency guard, occupancy check, same-room fee-leak rule, non-comparable warnings |
| R11 | Evidence expiry (stream links) | Weak proof | Page text + screenshots (own runner) + signed receipts stored durably |
| R12 | Secrets leakage | Account/credit loss | `.env` only, secret scan in CI, rotate leaked keys, never paste keys into prompts/commands/chat |
| R13 | Overclaiming in pitch | Credibility loss | Say only what is verified; claims discipline (§9.7); unverified items on the roadmap slide |
| R14 | Time (2-day build) | Missing the loop | Strict must-ship list and cut list (§12.4) |
| R15 | **(new)** Distribution: users don't come to a new site | No adoption | Extension (F9) inside the booking page; B2B channel; instant cached answers |
| R16 | **(new)** Weak evidence base (n = 1) | Headline not credible | Evidence dataset (§2.4); show +34.6% as "largest observed case" until done |
| R17 | **(new)** No validated customer | Market viability criterion weak | Dated interview plan (§13.1); honest wording until validated |
| R18 | **(new)** Incumbents show post-checkout prices or add fee transparency | Differentiation shrinks | Lead with proof + cross-site neutrality + B2B data, not just the gap; verify competitor facts (§2.5) |

---

## 15. Roadmap

**Phase 0 — Hackathon baseline (built, with known gaps).** Contract, pipeline, scoring, dedupe, handoff, recheck, history, fee glossary, report, saved-mode plumbing; Cleartrip verified live. **Known gaps:** Agoda only partially verified, Booking.com unresolved, no real saved run, discovery never run live, evidence dataset not built (§4.11).

**Phase 1 — Harden the face and the evidence (before/at the buildathon).** Evidence dataset (§2.4); record a real saved run; resolve Agoda/Booking evidence quality; currency/occupancy/same-room guards everywhere; discovery proven live; comparison UI polish; competitor table verified; first interviews logged.

**Phase 2 — Engine MVP (buildathon).** Own hybrid agent (Cleartrip) with measured benchmarks, price cache + freshness, tiered verification, receipt hash (signing next), Gemini integration, Cloud Run deployment; price-drop watch if time allows.

**Phase 3 — Distribution and scale (first 1–3 months).** Extension prototype + crowd observations (one site first), B2B pilot with the chosen segment, Agoda/Booking playbooks, scheduler for popular hotels, self-writing playbooks, outcome-pricing experiment.

**Phase 4 — Platform (3–9 months).** AI-agent API, regulation/consumer-group data products, more verticals, fintech/platform partnerships.

---

## 16. Open questions and decisions needed

1. **Team availability and city** for 20–21 Nov (all four members).
2. **Booking.com:** invest in INR/flow fixes or keep as an honest `unverified` result for now? (Latest attempt outcome to be confirmed.)
3. **Agoda run 2 evidence:** confirm room text shows 2 adults and that the listing price is the same room before using it in any pitch.
4. **Real TinyFish spend:** confirm actual usage on the dashboard (the code's balance reading looked stale) and which account/key the live site uses.
5. **Own-agent hosting:** local machines vs Cloud Run (headless Chromium) vs a VM; proxy/IP strategy.
6. **Gemini capabilities:** confirm model names and computer-use/vision availability at build time.
7. **Savings definition** for outcome pricing (reference price rules).
8. **Cache TTLs** per date proximity and hotel volatility.
9. **Legal review** scope before any regulator/journalist positioning or extension launch.
10. **Which first B2B segment** (travel agents vs corporate desks vs event planners) — decide after the first 3–5 interviews (§13.1).
11. **(new)** Who runs the evidence dataset, and on which platforms/hotels (§2.4)? Owner and deadline.
12. **(new)** Who are the 2–3 named competitors per row of §2.5, and what exactly does each show before checkout?

### 16b. Claims to verify before any external use (new in v2)

| # | Claim | Where it appears | Status |
|---|---|---|---|
| 1 | Agoda ~4–7% and Booking.com ~4% affiliate rates; Cleartrip/Indian programs unknown | §10.1, §10.2 | Unverified; read each program's terms |
| 2 | Agoda run 2: payable ₹12,936.93, +18.2%, 2 adults | §4.10, §10.2b | Re-check room text and same-room listing price |
| 3 | India's 2023 dark-pattern guidelines name drip pricing | F11 | Verify wording with counsel/official text before saying it |
| 4 | Agoda removes duplicated/fake/test bookings | §10.1, F8 | Confirm in program terms |
| 5 | Competitor behaviour (Google Hotels, meta-search, OTAs) | §2.5 | Check actual products |
| 6 | Hybrid agent "tens of seconds, near-zero LLM cost" | F4 | Hypothesis; benchmark |
| 7 | Buildathon dates, prize, criteria | §12.1 | Re-check startupbuildathon.com |
| 8 | Gemini model names / computer-use availability | §11 | Check at build time |
| 9 | Booking.com attempt 3 outcome | §4.10 | Confirm from `results/` |
| 10 | Actual TinyFish cost per run | §4.10, §10.2 | Read dashboard |

---

# Appendices

## Appendix A — API quick reference

See §4.4 and `docs/CONTRACT.md`, `docs/EVENTS.md`, `docs/openapi.json`, `docs/RUNBOOK_FRONTEND.md`.

`POST /api/search` bodies:

```json
// text mode
{"text": "Bengaluru, 20-21 Nov 2026, 2 people, breakfast, free cancellation, under 12k"}

// flat fields
{"destination":"Bengaluru","check_in":"2026-11-20","check_out":"2026-11-21",
 "guests":2,"rooms":1,"budget_per_night":12000,"deal_mode":"best_value",
 "must_have":{"breakfast":true,"free_cancellation":true}}

// target mode (skips discovery; used for live demos)
{"hotel_name":"La Marvella","platforms":["cleartrip","agoda","booking"],
 "destination":"Bengaluru","check_in":"2026-11-20","check_out":"2026-11-21",
 "guests":2,"rooms":1}
```

Results include: `_meta`, `search_request`, `travel_profile`, `hotels`, `listings`, `hotel_groups`, `offers`, `verdicts`, `handoff`, `rechecks`, `summary_strip`, and `complete`. Every offer carries status, reconciliation, cancellation category, blocker, price trail, fee lines (with `fee_kind`), evidence, transparency, `mock`.

## Appendix B — Environment variables and modes

| Variable | Purpose | Notes |
|---|---|---|
| `DATA_MODE` | `mock` / `fake` / `live` / `saved` | default mock |
| `TINYFISH_FAKE` | `1` = canned agent outputs | required for fake |
| `TINYFISH_API_KEY` | TinyFish access | `.env` only; never share |
| `ANTHROPIC_API_KEY`, `INTAKE_MODEL` | current intake LLM | to be replaced by Gemini config |
| `MAX_SPEND_USD` | per-search budget guard (default 4.0) | skips runs when exceeded |
| `MAX_CONCURRENT_RUNS` | semaphore (default 3) | confirm organiser limits |
| `AGENT_TIMEOUT_S` | per-run timeout (default 360; 600 live) | no retries |
| `DISABLE_LIVE` | `1` kills live/re-check spending | use on public deployments |
| `FAKE_SPEED` | fake-mode pacing | for demos/tests |

Planned: `AGENT_RUNNER=own|tinyfish|auto`, `GEMINI_MODEL`, cache TTL settings, signing key reference.

## Appendix C — Commands (Windows PowerShell)

```powershell
# API (repo root), fake mode needs no keys
py -m pip install -r api/requirements.txt
$env:DATA_MODE="fake"; $env:TINYFISH_FAKE="1"
py -m uvicorn api.main:app --port 8000

# Tests and checks
cd api; py -m pytest -q
py scripts/query_suite.py
py scripts/scan_secrets.py --git-history
py scripts/export_openapi.py

# One-hotel end to end (fake by default; live needs explicit flags and approval)
py scripts/e2e_one_hotel.py --hotel "La Marvella" --platforms Cleartrip
# py scripts/e2e_one_hotel.py --hotel "La Marvella" --platforms Cleartrip --live --yes-spend
```

Frontend (`web/`): `.env.local` with `NEXT_PUBLIC_DATA_MODE=live` and `NEXT_PUBLIC_API_URL=http://localhost:8000`, then `npm run dev`.

## Appendix D — Glossary

- **Listed price:** price shown on a listing/room-selection page before checkout.
- **Final payable:** amount on the payment page.
- **Fee leak %:** `(final − listing) / listing × 100`, observed on one run, same room only.
- **Gap excluding taxes:** `(final − taxes − listing) / listing × 100`, used in the evidence dataset (§2.4).
- **Fee kinds:** `tax`, `platform_fee`, `property_fee`, `add_on`, `other`.
- **Verified / unverified / blocked:** see §4.7.
- **Reconciliation:** fee lines sum to payable within ±1% (`ok`) or not (`mismatch`).
- **Comparable:** same guests/occupancy, nights, meal plan and cancellation category.
- **Playbook:** deterministic, assertion-checked script for walking one site's checkout.
- **Receipt:** signed, hashed bundle of the evidence for one verified price.
- **Hybrid agent:** playbooks + LLM only for recovery/extraction/verification.
- **Cache hit / TTL:** serving a stored verified price while it is still fresh.
- **Handoff pack:** selection card + deep link/QR + disclaimer for booking the winning offer.
- **Drip pricing:** revealing mandatory charges progressively through checkout.
- **Moat metric:** count of fresh verified hotel × platform × stay-date keys (§10.6).

## Appendix E — Pitch lines (updated in v2)

- **One-liner:** "TinyTravel is the verified all-in price layer for hotel booking: the real payable price on every site, with proof behind it."
- **30-second pitch:** "Hotel prices aren't final until the last checkout step. TinyTravel finds the real all-in price of the same hotel across sites, proves it with evidence, and tells you where to book. We verify once and serve many through a shared price database, so it's fast and cheap. Free for travellers, paid by travel businesses that need trustworthy quotes." (Use "paid by" only once §13.1 has a validated customer; otherwise "built for".)
- **Problem → solution paragraph (application):** "Hotel prices shown on listings are not the prices people pay. Taxes, convenience fees and add-ons appear only at the final checkout step, so finding the true cheapest option means walking several checkouts by hand. Listing scrapers and meta-search can't solve this, because the payable price exists only after interacting with checkout. TinyTravel verifies the final payable price of the same hotel across booking sites as a guest, never paying or logging in, attaches evidence to every price, and compares like for like (same room, guests, meal plan and cancellation terms). Verified prices are stored in a shared, time-stamped price database, so one verification serves many users, which makes the economics work and builds a data asset competitors can't copy by scraping listings. Gemini powers intake, page understanding and verification."
- **Business line:** "Travel agents and corporate desks are our first target customers for verified bulk quotes with proof; consumers are the free funnel, monetised through affiliate handoff and savings-based fees."
- **Moat line:** "We're building the verified all-in price database for travel, with signed proof behind every price."
- **Honesty line:** "If we can't prove it, we say so — blocked and unverified results are shown, never scored."
- **Evidence line (fill in from §2.4):** "Across [N] guest checkouts on [platforms] for [M] Bengaluru hotels, the final payable price was a median of [X]% above the listed price. Observed on these runs."

## Appendix F — Decision log (why we decided what we decided)

| Decision | Why |
|---|---|
| Walk real checkouts instead of scraping listings | Final price exists only at the end of checkout |
| Guest-only, dummy details, stop at payment | Safety, ToS posture, trust promise, clean evidence |
| Evidence required for `verified` | "Prove it" is the brand; prevents fabricated prices |
| Never convert currencies; null ≠ 0 | Avoid invented numbers and silent wrong comparisons |
| Currency, occupancy and same-room guards | Real runs returned USD and ambiguous room data |
| Contract-first (fixtures + pydantic + CI) | Frontend/backend cannot drift |
| Pure-function scoring with golden tests | Reproducible, auditable ranking |
| Suggested matches not merged into pricing | A false merge is worse than a missed one |
| Budget guard, concurrency limit, no retries | Credits are scarce; failed runs must be visible |
| Comparison stays the face of the product | It is the user's pain and the demo moment |
| Cache before more agents | Fixes unit economics and speed |
| Own **hybrid** agent, TinyFish as fallback | Cheaper/faster without losing resilience |
| Drop real-details/Google-login and captcha circumvention | Trust, security, ToS and unreliability |
| Extension for user-present data | Legitimate way to see member prices and reduce agent cost |
| Outcome-based pricing | Aligns incentives, avoids charging for failures |
| Signed receipts | Durable proof; unlocks B2B/disputes |
| Alerts only for price-drop rebooking | Humans approve money movement |
| **(v2)** Reframe as "verified all-in price layer" | Avoids head-on comparison with Google Hotels/meta-search; opens B2B and API paths |
| **(v2)** Build the evidence dataset before more features | n = 1 is an anecdote; cheapest credibility gain |
| **(v2)** Lead revenue with B2B, demote consumer affiliate | Consumer affiliate loses money per comparison without a high cache hit rate |
| **(v2)** Rank the extension (F9) and B2B (F11) higher | They answer distribution and revenue, our two weakest points |
| **(v2)** Add measured/estimated/unverified labels | Prevents overclaiming in the pitch |
| **(v2)** Trim the submission to F1–F6 plus one roadmap slide | A focused loop reads better than fourteen features |

## Appendix G — Sources used for facts in this doc

- Startup Buildathon India 2026 (Hack2skill/Google): https://startupbuildathon.com/ (dates, prize, criteria; re-check before relying on them).
- Affiliate commission figures (**unverified claims; verify before quoting**): https://track360.io/blog/agoda-affiliate-program-operator-teardown-2026, https://uppromote.com/affiliate-programs/hotel/, https://authorityhacker.com/hotel-affiliate-programs/, https://www.travelpayouts.com/blog/best-hotel-affiliate-program/amp/.
- Internal: `docs/BUILD_PLAN.md`, `docs/PHASED_PLAN.md`, `docs/CONTRACT.md`, `docs/EVENTS.md`, `docs/CONTRACT_CHANGES.md`, `docs/TINYFISH_NOTES.md`, `docs/GATE_REPORT.md`, `docs/RUNBOOK_FRONTEND.md`, `fixtures/real/`, `results/`.

*End of document. Edit this file when decisions change, and add a dated entry to the decision log.*
