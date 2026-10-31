# Frontend Runbook: TinyTravel Backend API

> **Audience**: Frontend Developer (Rithvik)  
> **Backend Version**: P0 Feature-Complete (Branch: `backend`)  
> **Base URL**: `http://127.0.0.1:8000` (or `http://localhost:8000`)  
> **CORS**: Enabled for `http://localhost:3000` (Next.js default) with full credentials and all methods.

---

## 1. Quick Start

### Working Directory
Always start the API server from the **repository root directory**:
```bash
# Verify current working directory is the repository root
pwd
# E:/tinytravel (or /path/to/tinytravel)
```

### Exact Start Command
From a fresh terminal in the repository root:

- **Windows (Python Launcher)**:
  ```powershell
  py -3.11 -m uvicorn api.main:app --port 8000 --reload
  ```

- **macOS / Linux / Activated Virtualenv**:
  ```bash
  uvicorn api.main:app --port 8000 --reload
  ```

### Verify Server Health
In a separate terminal:
```bash
curl http://127.0.0.1:8000/api/health
```
**Expected Response**:
```json
{"ok": true, "mode": "mock"}
```

---

## 2. Environment Variables & `DATA_MODE`

The backend supports 4 execution modes configured via `.env` or process environment variables:

| `DATA_MODE` | Purpose | Required Keys | API / Browser Spend |
|---|---|---|---|
| `mock` *(default)* | Instant responses serving fixed fixtures (`fixtures/demo_run.json` and `fixtures/sse_script.json`). Ideal for UI layout testing. | None | **$0.00** |
| `fake` | Executes the **real backend pipeline** (intake parsing, multi-agent discovery, hotel deduplication, target selection, checkout, fee leak calculation, and scoring) using deterministic simulated browser agents. | None | **$0.00** |
| `saved` | Replays saved real probe runs from previous test runs. | None | **$0.00** |
| `live` | Live execution using real TinyFish cloud browser agents against live OTA platforms. | `TINYFISH_API_KEY`<br>`ANTHROPIC_API_KEY` (optional) | Real cloud browser credits |

### Does `fake` Mode Need `TINYFISH_FAKE=1`?
**YES**. In `.env`, you must set:
```dotenv
DATA_MODE=fake
TINYFISH_FAKE=1
```
The TinyFish integration service (`api/services/tinyfish.py`) checks `os.getenv("TINYFISH_FAKE") == "1"` to bypass cloud SDK initialization and redirect agent calls to the local deterministic replay engine.

### Does `fake` Mode Work with Zero API Keys?
**YES (PROVEN)**.
- If `ANTHROPIC_API_KEY` is omitted, the intake engine automatically falls back to an offline deterministic regex/keyword parser (`api/services/intake.py`).
- If `TINYFISH_API_KEY` is omitted, `TINYFISH_FAKE=1` intercepts all browser agent executions and returns fixture streams without attempting network connections.
- Verified test with all keys removed:
  ```python
  # All keys cleared: TINYFISH_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
  # Pipeline run output:
  # Hotels found: 3, Offers found: 6, Verified: 5, Blocked: 1, Avg Fee Leak: 19.8%
  ```

---

## 3. CORS Configuration

CORS middleware is configured in `api/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Preflight Verification for `http://localhost:3000`
Tested via `OPTIONS /api/search` with header `Origin: http://localhost:3000`:
- **Status**: `200 OK`
- `Access-Control-Allow-Origin`: `http://localhost:3000`
- `Access-Control-Allow-Credentials`: `true`
- `Access-Control-Allow-Methods`: `DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT`
- `Access-Control-Allow-Headers`: `*`

The Next.js frontend running on `http://localhost:3000` can make direct `fetch()` or `EventSource` calls without proxying.

---

## 4. `POST /api/search` Request Payloads & Responses

All modes return an immediate HTTP 200 containing `{"search_id": "<sid>"}`. The frontend then subscribes to SSE at `/api/search/<sid>/stream` or polls `/api/search/<sid>/results`.

### Mode A: Text Mode (Natural Language)
Use when the user enters free-form text in the search input box.

**Request**:
```http
POST /api/search HTTP/1.1
Content-Type: application/json

{
  "text": "Bengaluru, 20-21 Nov 2026, 2 people, breakfast, free cancellation, under 12k"
}
```
**Response**:
```json
{
  "search_id": "a11022bc"
}
```

### Mode B: Flat-Field Mode (Structured Search)
Use when the user submits structured form fields (date pickers, guest counters, filter checkboxes).

**Request**:
```http
POST /api/search HTTP/1.1
Content-Type: application/json

{
  "destination": "Bengaluru",
  "check_in": "2026-11-20",
  "check_out": "2026-11-21",
  "guests": 2,
  "rooms": 1,
  "budget_per_night": 12000,
  "deal_mode": "best_value",
  "must_have": {
    "breakfast": true,
    "free_cancellation": true
  }
}
```
**Response**:
```json
{
  "search_id": "df39d0e6"
}
```

### Mode C: Target Mode (Fast-Track Single Hotel / Demo Segment)
Target mode bypasses broad OTA discovery and dispatches checkout verification agents directly to specific platforms for a named property (e.g. *La Marvella on Cleartrip*).

**Request**:
```http
POST /api/search HTTP/1.1
Content-Type: application/json

{
  "hotel_name": "La Marvella",
  "platforms": ["Cleartrip"],
  "destination": "Bengaluru",
  "check_in": "2026-11-20",
  "check_out": "2026-11-21",
  "guests": 2,
  "rooms": 1,
  "budget_per_night": 12000
}
```
**Response**:
```json
{
  "search_id": "1afd7dfa"
}
```

---

## 5. Target-Mode `ResultsResponse` Field Inspection

When querying `GET /api/search/{id}/results` for a target-mode run (e.g. *La Marvella on Cleartrip*), fields are structured as follows:

### Filled Fields
- `_meta`: `{"mock": true, "label": "TinyTravel Verification Run", "saved_run_label": null, "note": "..."}`
- `search_request`: Fully populated with destination, dates, guests, rooms, budget, must_have map, deal_mode, and currency.
- `travel_profile`: Inferred profile: `{"type": "couple", "group_size": 2, "nights": 1, "budget_band": "mid", "speed_preference": "thorough"}`.
- `hotels`: List with 1 item: `{"hotel_id": "h1", "canonical_name": "La Marvella", "area": "HSR Layout", "rating": 4.5}`. (**`rating` is filled: 4.5**).
- `hotel_groups`: List with 1 item: `{"hotel_id": "h1", "canonical_name": "La Marvella", "area": "HSR Layout", "match_status": "merged", "confidence": 0.96, "why": "Target mode: single hotel across platforms", "offer_ids": ["h1_cleartrip"]}`.
- `offers`: List with 1 verified offer (`h1_cleartrip`):
  - `status`: `"verified"`
  - `reconciliation`: `"ok"`
  - `price_shown_on_listing`: `8210.0`
  - `price_final_payable`: `11276.0`
  - `fee_leak_pct`: `37.3`
  - `fee_lines`: Breakdown items (Base Rate, Taxes & Fees, Service Charge).
  - `price_trail`: Array of observed checkpoints (`listing`, `room_selection`, `traveller_details`, `payment`).
  - `transparency`: Score breakdown (`total: 42`, `fee_leak: 3.4`, `evidence: 10`, etc.).
  - `evidence`: Screenshot / recording links and DOM text extracts.
- `verdicts`:
  - `deal_mode`: `"best_value"`
  - `hero_hotel_id`: `"h1"`
  - `ranking`: 1 item (`offer_id: "h1_cleartrip"`, `total: 93.2`, components, weights).
  - `overall`: `cheapest_verified: "h1_cleartrip"`, `safe_cheapest: "h1_cleartrip"`, `best_for_you: "h1_cleartrip"`, and headlines.
  - `per_hotel.h1`: Same picks and headlines for hotel `h1`.
- `handoff`: Full handoff package with deep link, base64 QR code PNG, selection card, and guest copy-paste details.
- `summary_strip`: `{"listings_found": 0, "unique_hotels": 1, "verified": 1, "unverified": 0, "blocked": 0, "avg_fee_leak_pct": 37.3}`.
- `complete`: `true`.

### Null / Empty Fields in Target Mode
- `listings`: `[]` (Empty list: broad OTA search discovery was bypassed).
- `rechecks`: `[]` (Empty list initially: only populated once `POST /api/offers/{id}/recheck` is called).
- `verdicts.non_comparable_warnings`: `[]` (Empty list: because only 1 platform offer exists in this run, there are no cross-platform room/meal plan mismatches).
- `offers[0].blocker`: `null` (Null: run reached payment page without anti-bot/login blockers).
- `offers[0].preselected_addons`: `[]` (Empty list: no pre-selected insurance/donation add-ons detected).
- `offers[0].urgency_or_scarcity_messages`: `[]` (Empty list: no artificial countdown banners detected).
- `offers[0].listing_page_text`: `null` (Raw DOM text dump omitted to save payload size; summarized in `evidence`).
- `offers[0].payment_page_text`: `null` (Omitted to prevent sensitive data leakage).

---

## 6. Status of `/handoff` and `/recheck` Endpoints

Both endpoints are **LIVE, fully implemented, and verified** (NOT 501 and NOT hardcoded mock only).

### 1. `GET /api/offers/{offer_id}/handoff`
- **Status**: **LIVE** (HTTP 200)
- **Implementation**: `api/services/handoff.py::build_handoff(offer)`
- **Capabilities**:
  - Dynamically builds affiliate/direct OTA deep link.
  - Generates real, scannable PNG QR code encoded in Base64 data URI (`data:image/png;base64,...`).
  - Prepares `selection_card` containing hotel name, room type, meal plan, cancellation terms, dates, guests, and verified final payable price.
  - Generates safe `copy_paste` dummy guest details (Name: `"Test Guest"`, Email: `test.guest+probe@example.com`, Phone: `9000000000`).
  - Attaches standard safety disclaimer.
- **Example Response**:
  ```json
  {
    "offer_id": "h1_cleartrip",
    "platform": "Cleartrip",
    "deep_link": "https://www.cleartrip.com/hotels/details/42069?c=20261120&chk_out=20261121&num_rooms=1&adults=2",
    "qr_png_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "qr_note": "Scan with phone to open exact room on Cleartrip",
    "selection_card": {
      "hotel": "La Marvella",
      "room_type": "Deluxe Double",
      "meal_plan": "Breakfast included",
      "cancellation": "Free cancellation until 18 Nov 2026, 12:00",
      "dates": "20-21 Nov 2026 (1 night)",
      "guests": 2,
      "expected_final_payable": 11276.0,
      "currency": "INR",
      "verified_at": "2026-10-31T14:42:00.555479+05:30"
    },
    "copy_paste": {
      "guest_name": "Test Guest",
      "email": "test.guest+probe@example.com",
      "phone": "9000000000"
    },
    "disclaimer": "Guest-only verification. We stop at the payment page and never complete transactions.",
    "mock": true
  }
  ```

### 2. `POST /api/offers/{offer_id}/recheck`
- **Status**: **LIVE** (HTTP 200)
- **Implementation**: `api/agents/recheck.py::recheck_offer(offer_id)`
- **Capabilities**:
  - Dispatches recheck agent to the target checkout URL.
  - Computes exact price delta (`new_price - original_price`), percentage change, and elapsed minutes.
  - Emits factual observation string (e.g. `"Price moved INR 11,276 -> INR 11,554 in 1 min (observed)."`).
  - Persists new observation to the SQLite `price_history` database table.
  - Updates the offer's transparency score stability component.
- **Example Response**:
  ```json
  {
    "recheck_id": "recheck_h1_cleartrip_1793437938",
    "offer_id": "h1_cleartrip",
    "status": "done",
    "previous": {
      "amount": 11276.0,
      "at": "2026-10-31T14:42:00.555479+05:30"
    },
    "current": {
      "amount": 11554.0,
      "at": "2026-10-31T14:42:18.686918+05:30"
    },
    "delta": 278.0,
    "delta_pct": 2.5,
    "elapsed_minutes": 1,
    "trail_diff": [
      {
        "step": "payment",
        "before": 11276.0,
        "after": 11554.0
      }
    ],
    "message": "Price moved INR 11,276 -> INR 11,554 in 1 min (observed).",
    "mock": true
  }
  ```

---

## 7. SSE Events & The Error Event Contract

The streaming endpoint is `GET /api/search/{id}/stream`.
Events are delivered in SSE envelope format:
```
event: <event_name>
data: {"t_ms": 350, "event": "<event_name>", "data": { ... }}
```

### The Error Event Shape
In `api/services/orchestrator.py` (lines 723-728) and aligned with `docs/EVENTS.md`:
```python
await emit_event(
    search_id,
    "error",
    {"message": str(exc), "recoverable": False},
    start_time,
)
```

The error SSE event payload is:
```json
{
  "message": "Human-readable description of the error",
  "recoverable": false,
  "code": null
}
```
- `message` (`string`): The error message.
- `recoverable` (`boolean`): Indicates whether the client can retry or recover (`false` for unhandled fatal errors).
- `code` (`string | null`): Optional error taxonomy code (default: `null`).

### Full SSE Event Reference
1. `parsed`: Travel requirements parsed from input.
2. `discovery_started`: Discovery agents dispatched across platforms.
3. `listings_found`: Count of listings found per platform.
4. `hotels_grouped`: Multi-platform deduplication and hotel grouping complete.
5. `agent_started`: Individual checkout agent starts probing an offer (contains `streaming_url` for live iframe).
6. `agent_progress`: Step progression (`"Selecting room"`, `"Filling guest details"`, `"Reached payment page"`).
7. `agent_done`: Agent completed run (`status`: `"verified"` | `"unverified"` | `"blocked"`).
8. `ranking_ready`: Pipeline complete; returns `hero_hotel_id`.
9. `error`: Stream or pipeline error (`{"message": "...", "recoverable": false, "code": null}`).
