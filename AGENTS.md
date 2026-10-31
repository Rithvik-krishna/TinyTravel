# TinyTravel Agent Guidelines

## Product & Safety Invariants
1. Never fabricate a price. No evidence = unverified. Unknown is never positive.
2. `verified` requires ALL: `reached_payment_page==true`, `price_final_payable!=null`, at least one evidence item, fee_lines sum to price_final_payable within +/-1%. If lines mismatch, set reconciliation="mismatch", not verified leak.
3. Agents are GUEST ONLY with dummy data (Name: "Test Guest", Email: test.guest+probe@example.com, Phone: 9000000000). STOP at payment page. Never pay, login, enter OTP, or store card/auth data.
4. State only observed facts ("price moved X to Y in N min"). Never assume cause or label platforms dishonest.
5. Blocked/unverified results are shown honestly with score=null (N/A).
6. Mock data carries `"mock": true`; saved runs carry `"saved": true` and capture timestamp.
7. Secrets stay in `.env` only (never committed, never logged, redact in logs).

## Contract Rules (Frontend <-> Backend)
- Contract baseline: `fixtures/demo_run.json` (GET /api/search/:id/results) and `fixtures/sse_script.json` (SSE).
- Additive changes only. Never rename, remove, or retype fields.
- Any change requires in the same commit: Pydantic models (`api/schemas.py`), fixtures, tests (`api/tests/`), and a dated entry in `docs/CONTRACT_CHANGES.md`.
- Amounts: JSON numbers in site currency (INR for demo). Unknown = `null`, never `0`.
- Timestamps: ISO-8601 with `+05:30`.
- Enums: `status` (verified|unverified|blocked), `cancellation_category` (free|partial|non_refundable), `blocker` (captcha|login|otp|timeout|other|null).

## Ownership & Git Workflow
- Nikhil: `api/**`, `fixtures/**`, `scripts/**`, `results/**` (branch: `backend`).
- Rithvik: `web/**` (branch: `frontend`). Do not edit `web/**` unless instructed.
- Shared: `docs/**`, `README.md`, `.github/**`, root configs.
- Merge flow: Work on own branch -> `git pull --rebase origin main` -> PR to `main` -> merge once CI green.
- Never force-push. Never commit `.env`, `node_modules`, `.venv`, `.next`, `*.db`.

## Backend Engineering Rules
- Python 3.12, async/await, Pydantic v2, type hints.
- Pure functions in `api/services/`, pytest tests in `api/tests/`. Run `cd api && pytest -q` before commits.
- No heavy dependencies without approval. No agent retry loops. Client timeout ~6 min.

## Report Format (end every response with this, <40 lines)
1) Files changed
2) Commands run + results (tests pass/fail counts)
3) Decisions and assumptions
4) Contract changes (or "none")
5) Blockers / open questions
6) Suggested next step
