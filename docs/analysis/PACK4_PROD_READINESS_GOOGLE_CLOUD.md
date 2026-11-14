# Pack 4 — Production-Readiness Audit for Google Cloud

**Scope:** Production-readiness audit of the TinyTravel repository for Google Cloud (Cloud Run, Cloud SQL, Secret Manager, Google AI).  
**Standard:** Every item categorized with status, risk, estimated effort in hours, and priority (P0/P1/P2). Output strictly formatted in tables.

---

## 1. Production-Readiness Audit Matrix

| Audit Item | Current Repository Status | Risk Level | Implementation Details / Gaps | Effort (Hours) | Priority |
|---|---|---|---|---|---|
| **Dockerfile & Containerization** | **MISSING** (No `Dockerfile` in root or `api/`) | **HIGH** | Cannot deploy to Cloud Run. Requires multi-stage Dockerfile based on `python:3.11-slim`, installing system libraries (`libnss3`, `libatk-bridge2.0-0`, `libx11-xcb1`) for headless Chromium Playwright support. | 3.0 h | **P0** |
| **Cloud Run Compute & Memory Limits** | **UNCONFIGURED** (Local uvicorn only) | **HIGH** | Headless browser execution crashes below 2 GiB RAM. Must set `--memory=2GiB`, `--cpu=2`, `--timeout=600s`, and **`--no-cpu-throttling`** so background agent execution is not halted. | 1.5 h | **P0** |
| **Cloud Run SSE Streaming Support** | **SUPPORTED** in FastAPI code | **LOW** | FastAPI returns `StreamingResponse` for `/api/search/{id}/events`. Cloud Run supports streaming natively provided request timeout is set to 600s+. | 0.5 h | **P0** |
| **Database: SQLite to Managed PostgreSQL** | **PARTIAL** (`sqlite3` in `api/db.py`) | **HIGH** | Cloud Run filesystems are ephemeral; local `tinytravel.db` resets on container restart or auto-scaling. Must refactor `api/db.py` to Google Cloud SQL (PostgreSQL) using SQLAlchemy or asyncpg. | 4.0 h | **P0** |
| **Authentication & Access Control** | **MISSING** (Public open endpoints) | **HIGH** | `/api/search` is open to the internet without auth. Any external visitor can trigger costly browser agent runs. Requires API key middleware for B2B and session tokens for web clients. | 3.0 h | **P0** |
| **Rate Limiting & Abuse Prevention** | **MISSING** | **HIGH** | No rate limiting on search or re-check endpoints. Vulnerable to budget exhaustion DoS. Requires IP-based rate limiting (`slowapi` or Redis/Cloud Memorystore). | 2.5 h | **P0** |
| **Cost Controls & Hard Circuit Breaker** | **PARTIAL** (Step cap in prompt, no global cap) | **HIGH** | If many concurrent queries arrive, spend can exceed budget. Requires global daily spend counter in database that automatically reverts to mock mode when threshold is reached. | 2.0 h | **P0** |
| **Secrets Management** | **LOCAL ONLY** (`.env` file via `dotenv`) | **MEDIUM** | `.env` is uncommitted (correct), but Cloud Run requires automated mounting from **Google Secret Manager** via `--set-secrets`. | 1.5 h | **P0** |
| **CORS Configuration** | **INSECURE** (`allow_origins=["*"]` with `allow_credentials=True`) | **MEDIUM** | In `api/main.py`, wildcard origin with credentials violates modern CORS browser specs. Must restrict to designated frontend domain (`https://tinytravel.app`, `http://localhost:3000`). | 0.5 h | **P0** |
| **CI/CD Pipeline (Google Cloud Deployment)** | **TEST ONLY** (`.github/workflows/ci.yml`) | **MEDIUM** | CI runs pytest and secret scans on PRs, but lacks automated CD deployment to Google Cloud Run via Google Workload Identity Federation. | 2.0 h | **P1** |
| **Logging & Observability** | **BASIC** (Standard Python `logging` to stdout) | **LOW** | Cloud Run automatically captures stdout to Cloud Logging. Needs structured JSON logging (`google-cloud-logging`) for automated error alerting and latency metrics. | 2.0 h | **P1** |
| **Security: Prompt Injection** | **PARTIAL** (Basic prompt concatenation in `intake.py`) | **MEDIUM** | Natural language user text is directly injected into LLM prompt. Must wrap in strict XML delimiters (`<user_query>...</user_query>`) and enforce JSON schema outputs. | 1.5 h | **P1** |
| **Security: HTML Escaping & XSS** | **IMPLEMENTED** (PR #16 / `reporting.py`) | **LOW** | Dynamic values rendered in HTML reports are escaped via `html.escape()`. Invariant verified by tests. | 0.0 h | **P2** |
| **Security: Path Traversal** | **IMPLEMENTED** (PR #15 / `evidence.py`) | **LOW** | Evidence file paths sanitized using `Path.resolve()` and restricted to allowed directories. | 0.0 h | **P2** |
| **Test Coverage & Regressions** | **EXCELLENT** (100 passing tests in `api/tests`) | **LOW** | Full unit and contract golden test suite. Requires Cloud SQL mock integration tests before production launch. | 2.5 h | **P1** |
| **Privacy Policy & Terms Pages** | **MISSING** in `web/` | **MEDIUM** | Required for Google OAuth, Chrome Extension Store submission, and CCPA/GDPR compliance. | 2.0 h | **P1** |

---

## 2. Inventory of External AI & Agent Dependencies: Migration to Google Gemini

| File Location | Current External Dependency | Current Role / Usage | Target Google Migration Component | Migration Effort (Hours) | Priority |
|---|---|---|---|---|---|
| `api/services/intake.py` | **Anthropic Claude API** (`anthropic`) | Natural language search string parsing into structured JSON (`SearchRequestOut`) | **Google Gemini 2.5 Flash** via `google-genai` SDK with structured JSON schema | 1.5 h | **P0** |
| `api/services/tinyfish.py` | **TinyFish SDK** (`tinyfish`) | Remote browser automation sandbox for multi-step checkout execution | **Playwright + Google Gemini 2.5 Pro Multimodal** (DOM & visual fee extraction) | 3.5 h | **P0** |
| `api/services/fees.py` | Rule-based heuristics | Fee line taxonomy classification (`tax`, `service_fee`, `discount`, `add_on`) | **Google Gemini 2.5 Flash** few-shot classification for ambiguous OTA fee labels | 1.0 h | **P1** |
| `api/services/reporting.py` | Jinja2 / string templates | Plain-language verdict generation ("Cheapest Verified", "Fee Leak Alert") | **Google Gemini 2.5 Flash** for personalized natural-language booking recommendations | 1.5 h | **P1** |

---

## 3. Total Migration & Production Hardening Summary

| Priority Level | Total Items | Estimated Engineering Hours | Target Milestone |
|---|---|---|---|
| **Priority P0 (Blockers for Cloud Run & Security)** | 9 items | 18.0 hours | City Buildathon Sprint (20–21 Nov 2026) |
| **Priority P1 (Hardening, Observability & Compliance)** | 5 items | 9.0 hours | Pre-Showcase Week (22–26 Nov 2026) |
| **Priority P2 (Post-Launch Refinements)** | 2 items | 2.5 hours | Post-Buildathon / Enterprise Cohort |
| **Total** | **16 items** | **29.5 hours** | Complete Google Cloud Migration |
