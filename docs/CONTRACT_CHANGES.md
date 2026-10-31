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
