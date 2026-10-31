# TinyTravel
The price you see isn't the price you pay.

## Run (mock mode, no keys needed)
```
# terminal 1
cd api && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# terminal 2
cd web && cp ../.env.example .env.local && npm install && npm run dev
```
Open http://localhost:3000/search

## Modes
`NEXT_PUBLIC_DATA_MODE=mock` (UI reads `fixtures/*.json`, no API needed) or `live` (UI calls the API).
`DATA_MODE=mock|live` for the API. Live agents are TODO stubs in `api/agents/`.

## Layout
web/ Next.js UI · api/ FastAPI · fixtures/ mock + saved runs · results/ probe outputs
All mock data carries `"mock": true` and the UI shows a MOCK DATA badge.

## Branches and workflow
- `backend` (Nikhil: `api/**`, `fixtures/**`, `scripts/**`, `results/**`)
- `frontend` (Rithvik: `web/**`) | `docs/**`, `README.md`, `.github/**` are shared
- `main` is stable release (protected: PR + green CI required); `demo` is presentation branch
- Rebase before push (`git pull --rebase origin main`), open PR to `main`, never force-push
