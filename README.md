# TinyTravel

> **The price you see isn't the price you pay.**

TinyTravel sends autonomous [TinyFish](https://docs.tinyfish.ai) browser agents through real hotel checkouts, **as a guest and without ever paying**. It records the true all-in payable price with evidence, filters out unfair comparisons, and hands you a ready-to-pay link.

Built for *Swim with TinyFish* (Bangalore, 31 Oct 2026).

---

## Table of contents

1. [What it does](#what-it-does)
2. [Safety and honesty invariants](#safety-and-honesty-invariants)
3. [Proven result](#proven-result)
4. [Architecture](#architecture)
5. [Repository layout](#repository-layout)
6. [Quick start](#quick-start)
7. [Data modes](#data-modes)
8. [Configuration](#configuration)
9. [API reference](#api-reference)
10. [Live event stream (SSE)](#live-event-stream-sse)
11. [Verification, scoring and ranking](#verification-scoring-and-ranking)
12. [Frontend routes](#frontend-routes)
13. [Scripts](#scripts)
14. [Testing and CI](#testing-and-ci)
15. [Contract rules](#contract-rules)
16. [Team, branches and workflow](#team-branches-and-workflow)
17. [Documentation index](#documentation-index)
18. [Known limitations](#known-limitations)

---

## What it does

1. **Intake**: one sentence ("Bengaluru, 20-21 Nov, 2 people, breakfast, free cancellation, under 5k") is parsed into a structured, editable request.
2. **Discovery**: agents collect candidate hotels from Cleartrip, Agoda and Booking.com.
3. **Dedupe and normalize**: listings for the same hotel are grouped across platforms, and only comparable room/package offers go forward.
4. **Checkout verification**: one agent per hotel and platform walks the guest checkout with dummy details, records a `price_trail` (listing, room, traveller details, payment) and stops at the payment page.
5. **Evidence**: every price carries evidence (recording link, text snippets, timestamp, source URL).
6. **Scoring**: Fee Leak %, a 0-100 transparency score, and three verdicts: cheapest verified, safe-cheapest (free cancellation), best for you.
7. **Handoff Pack**: deep link, QR code, selection card and copy-paste details. **The user logs in and pays themselves.**
8. **Re-check**: re-run one offer and diff the price trail to show real drift.

Example verdict: *"Book Hotel X on Cleartrip. You'll pay 4,069, not the 3,499 shown."*

## Safety and honesty invariants

These are enforced in code and tests, not just convention.

| # | Rule |
|---|------|
| 1 | **Never fabricate a price.** No evidence means `unverified`. Unknown is never treated as positive. |
| 2 | `verified` requires **all** of: `reached_payment_page == true`, `price_final_payable != null`, at least one evidence item, and fee lines summing to `price_final_payable` within +/-1%. A mismatch sets `reconciliation="mismatch"` and the offer is not verified. |
| 3 | Agents are **guest only** with dummy data (Name `Test Guest`, Email `test.guest+probe@example.com`, Phone `9000000000`). They **stop at the payment page**. They never pay, log in, enter an OTP, or store card/auth data. |
| 4 | State only observed facts ("price moved X to Y in N min"). Never assume a cause or label a platform dishonest. |
| 5 | Blocked or unverified results are shown honestly with `score = null` (N/A). |
| 6 | Mock data carries `"mock": true`. Saved runs carry `"saved": true` and a capture timestamp. |
| 7 | Secrets live in `.env` only: never committed, never logged, redacted in logs. |

## Proven result

The 14:00 gate run executed a real end-to-end checkout on Cleartrip for **La Marvella, Bengaluru** (20-21 Nov 2026, 2 adults) with a live TinyFish agent:

| | |
|---|---|
| Listing price shown | 8,867 |
| Final payable (payment page) | 11,933 |
| **Fee leak** | **+34.6%** |
| Reconciliation | `ok` (0.00 difference) |
| Cancellation | `non_refundable` |

A second run reached the payment page but its fee lines did not reconcile, so the engine correctly flagged `reconciliation=mismatch` and marked it `unverified`. Full detail, evidence and costs are in [`docs/GATE_REPORT.md`](docs/GATE_REPORT.md); the verified fixture is [`fixtures/real/gate_la_marvella_cleartrip.json`](fixtures/real/gate_la_marvella_cleartrip.json).

## Architecture

```
Next.js UI  ──►  FastAPI  ──►  Orchestrator
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
 Discovery (TinyFish)    Checkout probes (TinyFish)      Re-check
        │                         │                         │
        ▼                         ▼                         ▼
   Listings ──► Dedupe ──► Normalize ──► Evidence store (SQLite)
                                  │
                      Scoring + Ranking + Verdicts
                                  │
                SSE stream ──► Live dashboard / Verdict / Handoff
```

Backend building blocks:

| Module | Role |
|---|---|
| `api/main.py` | FastAPI app, routes, CORS, SSE streaming |
| `api/services/intake.py` | Sentence to structured request (optional LLM via `ANTHROPIC_API_KEY`) |
| `api/services/orchestrator.py` | Runs a search end to end, concurrency and spend caps, event emission |
| `api/services/tinyfish.py` | TinyFish SDK wrapper, schema cleaning, secret redaction, fake mode |
| `api/agents/discovery.py` / `checkout.py` / `recheck.py` | The three agent types |
| `api/services/dedupe.py` / `normalize.py` | Same-hotel matching (RapidFuzz) and offer normalization |
| `api/services/scoring.py` | Fee leak, reconciliation, status, transparency score, ranking, verdicts |
| `api/services/evidence.py` / `handoff.py` | Evidence handling, deep link and QR handoff |
| `api/schemas.py` / `models.py` / `events.py` | Pydantic v2 contract models |
| `api/db.py` | Persistence of searches and replayable events |

## Repository layout

```
tinytravel/
├── api/            FastAPI backend (Python 3.12, Pydantic v2)
│   ├── agents/       discovery, checkout, recheck agents
│   ├── services/     pure-function pipeline stages
│   └── tests/        pytest suite
├── web/            Next.js 14 + React 18 + Tailwind frontend
│   ├── app/          routes (landing, search, investigation, verdict, ...)
│   ├── components/   UI (landing/, flow/, shared tiles and dialogs)
│   └── lib/          data source, SSE hook, formatting
├── fixtures/       contract baseline: demo_run.json, sse_script.json, real/ saved runs
├── results/        raw probe and gate-run outputs
├── scripts/        probe_site.py, e2e_one_hotel.py, export_openapi.py
├── docs/           contract, events, plans, gate report, TinyFish notes
├── .github/        CI workflow
└── AGENTS.md       engineering guidelines for contributors and coding agents
```

## Quick start

Prerequisites: **Python 3.12**, **Node 20**, npm. No API keys are needed for mock mode.

### 1. Backend

```bash
cd api
python -m venv .venv
```

Activate the virtualenv, then install and run:

```bash
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
pip install -r requirements.txt
```

```bash
uvicorn main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/health> returns `{"ok": true, "mode": "mock"}`. Interactive docs are at <http://localhost:8000/docs>.

### 2. Frontend

```bash
cd web
cp ../.env.example .env.local   # PowerShell: Copy-Item ..\.env.example .env.local
npm install
npm run dev
```

Open <http://localhost:3000> for the landing page, or <http://localhost:3000/search> to start a search.

## Data modes

| Layer | Variable | Values | Behaviour |
|---|---|---|---|
| UI | `NEXT_PUBLIC_DATA_MODE` | `mock` (default), `live` | `mock` reads `fixtures/*.json` directly, no API needed. `live` calls the API. |
| API | `DATA_MODE` | `mock` (default), `fake`, `live` | `mock` serves `fixtures/demo_run.json` and replays `fixtures/sse_script.json`. `fake` runs the full real pipeline against simulated TinyFish agents (no spend). `live` runs real TinyFish browser agents (costs money). |
| API | `TINYFISH_FAKE=1` | | Forces simulated agents regardless of mode. Used by the test suite. |

Recommended progression: `mock` for UI work, `fake` to exercise the pipeline, `live` only for deliberate verification runs.

## Configuration

Copy `.env.example` to `.env` (API) and `web/.env.local` (UI). Never commit them.

| Variable | Default | Purpose |
|---|---|---|
| `TINYFISH_API_KEY` | none | Required for `DATA_MODE=live`. |
| `DATA_MODE` | `mock` | API mode (see above). |
| `NEXT_PUBLIC_DATA_MODE` | `mock` | UI mode. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL used by the UI. |
| `ANTHROPIC_API_KEY` | none | Optional, used by intake parsing. |
| `INTAKE_MODEL` | built-in default | Model used by intake parsing. |
| `MAX_CONCURRENT_RUNS` | `3` | Parallel TinyFish agents. |
| `MAX_SPEND_USD` | `4.0` | Spend ceiling per search. |
| `AGENT_TIMEOUT_S` | `360` | Per-agent client timeout (about 6 min). |
| `FAKE_SPEED` | `0.01` | Time scale for fake agents. |

## API reference

Base URL: `http://localhost:8000`. The generated schema is committed at [`docs/openapi.json`](docs/openapi.json) (regenerate with `scripts/export_openapi.py`).

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | `{ok, mode}` |
| `POST` | `/api/search` | Start a search. Body: `text` and/or structured fields (`destination`, `check_in`, `check_out`, ...), plus optional `hotel_name` and `platforms` for **target mode**. Returns `{search_id}`. |
| `GET` | `/api/search/{id}/stream` | SSE progress stream. Late subscribers get stored events replayed first. Optional `speed` query for mock replay. |
| `GET` | `/api/search/{id}/results` | Final `ResultsResponse` (offers, hotel groups, verdicts, summary strip). `404` if unknown or not ready. |
| `POST` | `/api/offers/{oid}/recheck` | Re-check an offer's price. *Currently served from the mock fixture.* |
| `GET` | `/api/offers/{oid}/handoff` | Handoff Pack. *Currently served from the mock fixture.* |

Start a search:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"text": "Bengaluru, 20-21 Nov, 2 people, breakfast, free cancellation, under 5k"}'
```

## Live event stream (SSE)

Nine events, in this order for a normal run (full payloads in [`docs/EVENTS.md`](docs/EVENTS.md)):

`parsed` → `discovery_started` → `listings_found` → `hotels_grouped` → `agent_started` → `agent_progress` (repeated) → `agent_done` → `ranking_ready`, with `error` on a fatal failure.

`agent_started` carries a `streaming_url` that the UI embeds as a live browser tile. `agent_done.status` is `verified`, `unverified` or `blocked`.

## Verification, scoring and ranking

**Fee Leak %** is `(price_final_payable - listing_price) / listing_price`, computed only from observed values; it is `null` when either is missing.

**Transparency score** (0-100, computed only for verified offers, `null` otherwise):

| Component | Max | Rule |
|---|---|---|
| Fee leak | 50 | `50 * (1 - leak / 40)`, floored at 0 |
| Add-ons and pressure | 20 | `20 - 5 per pre-selected add-on - 5 per urgency/scarcity message`, floored at 0 |
| Price stability | 20 | `20 * (1 - pct_change / 10)` from a re-check; skipped if none |
| Evidence | 10 | Proportional to listing, room and payment evidence present |

Without a re-check, the remaining components are re-normalised and the note reads *"observed on this run; stability N/A, weights re-normalised"*.

**Verdicts**: cheapest verified, safe-cheapest (free cancellation), and best for you, driven by the user's deal mode (`lowest_price`, `best_value`, `most_transparent`).

## Frontend routes

| Route | Purpose |
|---|---|
| `/` | Landing page: gap explainer, live replay, proof, safety, FAQ |
| `/book` | Booking entry page |
| `/onboarding` | Skippable 5-step "Travel DNA" chips |
| `/search` | Sentence search with editable chips |
| `/investigation` | Live agent tiles driven by SSE |
| `/compare` | Cross-platform offer comparison |
| `/verdict` | Verdict card, fee explainer, handoff |
| `/hotel/[hotelId]` | Per-hotel detail and price trail |
| `/evidence` | Evidence viewer |

Stack: Next.js 14 (App Router), React 18, Tailwind CSS 3, TypeScript, `lucide-react`, `qrcode.react`.

## Scripts

All scripts run from the repo root.

| Script | Purpose |
|---|---|
| `scripts/e2e_one_hotel.py` | Target-mode end-to-end run for one hotel. Flags: `--hotel`, `--platforms`, `--destination`, `--check-in`, `--check-out`, `--guests`, `--rooms`, `--budget`, `--deal-mode`, `--live`, `--yes-spend`. Without `--live` it uses simulated agents. Live mode requires `--yes-spend`. |
| `scripts/probe_site.py` | Probe a single platform's checkout feasibility. |
| `scripts/export_openapi.py` | Regenerate `docs/openapi.json`. |

```bash
python scripts/e2e_one_hotel.py --hotel "La Marvella" --platforms Cleartrip
```

## Testing and CI

```bash
cd api && pytest -q                 # backend: contract, golden, pipeline, dedupe, checkout, tinyfish
cd web && npm run typecheck         # frontend types
cd web && npm run build             # production build
```

Run `pytest -q` before every commit. GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the backend tests on Python 3.12 and the frontend install and build on Node 20 for every push and pull request.

## Contract rules

The frontend and backend are coupled through `fixtures/demo_run.json` (results) and `fixtures/sse_script.json` (SSE).

- **Additive changes only.** Never rename, remove or retype a field.
- Any change lands in one commit with: Pydantic models (`api/schemas.py`), fixtures, tests (`api/tests/`), and a dated entry in [`docs/CONTRACT_CHANGES.md`](docs/CONTRACT_CHANGES.md).
- Amounts are JSON numbers in site currency (INR for the demo). Unknown is `null`, **never `0`**.
- Timestamps are ISO-8601 with `+05:30`.
- Enums: `status` = `verified | unverified | blocked`; `cancellation_category` = `free | partial | non_refundable`; `blocker` = `captcha | login | otp | timeout | other | null`.

## Team, branches and workflow

| Owner | Area | Branch |
|---|---|---|
| Nikhil | `api/**`, `fixtures/**`, `scripts/**`, `results/**` | `backend` |
| Rithvik | `web/**` | `frontend` |
| Shared | `docs/**`, `README.md`, `.github/**`, root configs | n/a |

- `main` is the stable branch (PR and green CI required); `demo` is the presentation branch.
- Work on your own branch, run `git pull --rebase origin main`, open a PR to `main`, and merge once CI is green.
- **Never force-push.** Never commit `.env`, `node_modules`, `.venv`, `.next` or `*.db`.

Backend conventions: Python 3.12, async/await, Pydantic v2, type hints, pure functions in `api/services/`, no heavy dependencies without approval, no agent retry loops.

## Documentation index

| Doc | Contents |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Invariants and engineering rules |
| [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) | Full build plan, probe findings, scope, user journey |
| [`docs/PHASED_PLAN.md`](docs/PHASED_PLAN.md) | Phase-by-phase delivery plan |
| [`docs/CONTRACT.md`](docs/CONTRACT.md) | Data contract |
| [`docs/CONTRACT_CHANGES.md`](docs/CONTRACT_CHANGES.md) | Dated contract changelog |
| [`docs/EVENTS.md`](docs/EVENTS.md) | SSE event payloads |
| [`docs/GATE_REPORT.md`](docs/GATE_REPORT.md) | Real end-to-end gate verification |
| [`docs/TINYFISH_NOTES.md`](docs/TINYFISH_NOTES.md) | TinyFish SDK and schema findings |
| [`docs/OWNERSHIP.md`](docs/OWNERSHIP.md) | Ownership and merge flow |
| [`docs/openapi.json`](docs/openapi.json) | Generated OpenAPI schema |

## Known limitations

- A live checkout run takes roughly 2.5-5 minutes, so large live demos are not practical; use saved runs (`fixtures/real/`) or `fake` mode.
- Platforms verified so far: Cleartrip, Agoda, Booking.com. MakeMyTrip, Goibibo and EaseMyTrip were blocked or timed out in probes (see `docs/BUILD_PLAN.md`).
- The TinyFish SDK does not return downloadable screenshots; evidence is a session recording link plus extracted page text snippets.
- `recheck` and `handoff` endpoints still return mock fixture data.
- Only what is observed on a run is reported. TinyTravel does not infer why a price differs.
