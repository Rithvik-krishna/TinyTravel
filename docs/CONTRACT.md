# TinyTravel API Contract

Source of truth for frontend (`web/`) and backend (`api/`). Baseline: `fixtures/demo_run.json` & `fixtures/sse_script.json`.

## Endpoints
- `POST /api/search`: Accepts `{"text": "..."}` or structured `SearchRequest`, plus optional target mode `{"hotel_name": "...", "platforms": [...]}`. Returns `{"search_id": "<id>"}`.
- `GET /api/search/:id/stream`: Server-Sent Events (SSE) emitting progress and agent status envelopes.
- `GET /api/search/:id/results`: Returns full `ResultsResponse` with verified offers, verdicts, and groups.
- `POST /api/offers/:id/recheck`: Re-probes the specific offer; returns `Recheck` diff object.
- `GET /api/offers/:id/handoff`: Returns ready-to-pay `HandoffPack` with deep link and copy-paste details.

## Enums
- `status`: `verified` | `unverified` | `blocked`
- `cancellation_category`: `free` | `partial` | `non_refundable` (`null` when blocked/unverified)
- `reconciliation`: `ok` | `mismatch` (`null` when blocked/unverified)
- `blocker`: `captcha` | `login` | `otp` | `timeout` | `other` (`null` when unblocked)
- `deal_mode`: `lowest_price` | `best_value` | `most_transparent`
- `match_status`: `merged` (confidence >= 0.90) | `suggested` (0.75 <= confidence < 0.90)

## Null Semantics & Scoring
- **Unknown = `null`, never `0`**. Zero represents free / no fee.
- Blocked and unverified offers are shown honestly: `price_final_payable: null`, `fee_leak_pct: null`, `transparency.score: null` (rendered in UI as N/A).
- Score is calculated only on verified offers.

## Verification Rule
An offer is `status: "verified"` if and only if ALL criteria are met:
1. `reached_payment_page == true`
2. `price_final_payable != null`
3. `len(evidence) >= 1` (contains at least one screenshot/recording/page_text)
4. `fee_lines` sum reconciles with `price_final_payable` within +/-1% tolerance.
If fee lines fail tolerance, price is preserved but `reconciliation = "mismatch"` (not verified leak).

## Units & Formats
- **Amounts**: Numeric values in site currency (INR for demo). No client/server currency conversion.
- **Timestamps**: ISO-8601 strings with timezone offset (e.g. `2026-10-31T11:45:00+05:30`).

## Data Mode Flags
- `mock: true`: Indicates synthetic fixture data. Defaults to `false` for live agent runs.
- `saved: true`: Indicates a recorded replay of a past real agent run with capture timestamp.
