# Contract Changes Log

This is an append-only log tracking all changes to the API and SSE contracts between the backend and frontend.

## Contract Rules
- **Additive changes only**: Never rename, remove, or change the data type of an existing field.
- **Atomic updates**: Any contract change must be accompanied in the exact same commit by updates to:
  1. Pydantic models in `api/schemas.py`
  2. Fixtures in `fixtures/demo_run.json` and/or `fixtures/sse_script.json`
  3. Tests in `api/tests/`
  4. A dated entry added below in this document.
- **Amounts**: JSON numbers in the currency shown on the site (INR for demo). Never convert currencies. Unknown values must be `null`, never `0`.
- **Timestamps**: ISO-8601 with `+05:30`.
- **Enums**:
  - `status`: `verified` | `unverified` | `blocked`
  - `cancellation_category`: `free` | `partial` | `non_refundable`
  - `blocker`: `captcha` | `login` | `otp` | `timeout` | `other` | `null`

---

## Change Entries
<!-- Format:
### YYYY-MM-DD - <Who>
- **Field / Event**: `<field_or_event_name>` (added to `<schema/endpoint>`)
- **Type**: `<data_type>`
- **Why**: `<rationale>`
- **Fixtures updated**: Yes / No
-->

### 2026-10-31 - Nikhil
- **Initial Baseline**: Documented initial contract based on `fixtures/demo_run.json` and `fixtures/sse_script.json`.
- **Fixtures updated**: N/A (baseline establishment)

### 2026-10-31 - Nikhil
- **Executable Contract**: Formalized full models in `api/models.py` (`extra="forbid"`), SSE models in `api/events.py`, and exported `docs/openapi.json`.
- **Field / Event**: Added `SearchInput` to `POST /api/search` accepting `text`, structured search fields, and target mode fields (`hotel_name: str`, `platforms: list[str]`). Added `response_model` to all endpoints.
- **Why**: Prevent frontend/backend contract drift; enable live target-mode probing.
- **Fixtures updated**: No (fixtures remain canonical source of truth and validated 100% against new models).

### 2026-10-31 - Nikhil
- **Page Text Evidence Fields**: Added optional `listing_page_text: Optional[str] = None` and `payment_page_text: Optional[str] = None` to `ProbeResult` and `Offer`.
- **Type**: `Optional[str]` (defaults to `None`)
- **Why**: Captures verbatim text snippets from listing and payment pages to serve as verifiable `page_text` evidence without fabricating screenshot URLs.
- **Fixtures updated**: No (purely additive optional fields, existing fixtures validate with extra="forbid").

### 2026-10-31 - Nikhil
- **Results Complete Flag**: Added optional `complete: Optional[bool] = None` to `ResultsResponse`.
- **Type**: `Optional[bool]` (defaults to `None`)
- **Why**: Allows partial results inspection via `GET /api/search/:id/results` while runs are in progress, signaling completion status additively.
- **Fixtures updated**: No (purely additive optional field, existing fixtures validate with extra="forbid").

### 2026-10-31 - Nikhil
- **Fee Classification and Remaining Endpoints**:
  - **Fee Kind Attribute**: Added `fee_kind: Optional[FeeKind] = "other"` to `FeeLine` (`"tax"` | `"platform_fee"` | `"property_fee"` | `"add_on"` | `"other"`).
  - **New Endpoints**:
    1. `GET /api/history`: historical price ledger records for a hotel, ordered newest first (`list[PriceHistoryItem]`).
    2. `GET /api/fee-glossary`: static dictionary of explanations for common travel fee lines (`dict[str, FeeGlossaryItem]`).
    3. `GET /api/search/{sid}/report`: self-contained printable HTML evidence report (`HTMLResponse`).
    4. `GET /api/offers/{oid}/report-fee-draft`: polite, factual draft inquiry message for observed fees (`FeeDraftResponse`).
  - **Live Partial Results**: `summary_strip` counters (`listings_found`, `unique_hotels`, `verified`, `unverified`, `blocked`, `avg_fee_leak_pct`) are kept continuously updated in `ResultsResponse` during search execution.
- **Why**: Completes all remaining backend requirements, enables UI fee categorization, and provides transparent evidence reporting.
- **Fixtures updated**: Yes (`fixtures/demo_run.json` and `fixtures/real/gate_la_marvella_cleartrip.json` updated with classified `fee_kind` on each fee line).

### 2026-10-31 - Nikhil
- **Saved Mode & Fixture Replay Fields**:
  - Added `saved: Optional[bool] = False` and `saved_at: Optional[str] = None` to `MetaInfo` in `api/models.py`.
  - Added `saved: Optional[bool] = False` and `speed: Optional[float] = None` to `ScriptFile` in `api/events.py`.
  - Added `DATA_MODE=saved` support across `POST /api/search`, `GET /api/search/{id}/results`, `GET /api/search/{id}/stream`, `POST /api/offers/{id}/recheck`, and `GET /api/offers/{id}/handoff`.
  - Added static evidence fallback route `/evidence/{file_path:path}` checking `evidence/` and `fixtures/evidence/`.
- **Why**: Allows replaying a full, labelled real investigation without external network requests or credit spend, adhering to strict contract validation.
- **Fixtures updated**: Yes (`fixtures/saved_run.json` and `fixtures/saved_sse_script.json` created).

### 2026-10-31 - Nikhil
- **Price History Ledger & Reporting Fix-ups**:
  - Added optional `mock: Optional[bool] = False` to `PriceHistoryItem` in `api/models.py`.
  - Added optional `include_mock: bool = False` query parameter to `GET /api/history` in `api/main.py`.
  - Removed demo seeding from `api/db.py`; only real observations returned by default (empty list when no real records exist).
  - Sanitized HTML reporting with strict `html.escape` across all dynamic fields (preventing XSS).
  - Updated `report-fee-draft` to cite only `platform_fee`, `property_fee`, and `add_on` lines, excluding taxes from fees.
- **Why**: Ensures purity of historical observations, guarantees XSS safety in evidence reports, and isolates discretionary fees from statutory taxes in inquiry drafts.
- **Fixtures updated**: No (purely additive optional field).



