# TinyTravel Demo Runbook

Complete operational guide for running and demonstrating TinyTravel's autonomous hotel verification engine.

---

## 1. Quickstart & Service Startup

### Backend API
Ensure Python 3.11/3.12 virtual environment is active with dependencies installed:
```powershell
# In repository root
cd e:\tinytravel\api
py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API Health Check: `http://localhost:8000/docs` (Swagger UI) or `GET http://localhost:8000/api/budget`.

### Frontend Web UI
```powershell
# In repository root
cd e:\tinytravel\web
npm run dev
```
Open `http://localhost:3000` in the browser.

---

## 2. Operating Modes (`DATA_MODE`)

Configure via `.env` or prefix before running:

| Mode | Env Var | Latency | Network Required | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Saved Real Run** (Recommended for Demos) | `DATA_MODE=saved` | < 100 ms | No | Serves fully verified, real captured runs from `fixtures/saved_run.json` (`mock: false, saved: true`) with verbatim screenshots and reconciled fee lines. Zero risk of live platform flakiness during presentations. |
| **Live Probing** | `DATA_MODE=live` | 10–25 s | Yes (Internet) | Spawns autonomous Playwright guest agents against Cleartrip and Booking.com, navigating in real-time and stopping strictly at the payment review page. |
| **Mock Development** | `DATA_MODE=mock` | < 50 ms | No | Synthetic test fixtures for rapid offline contract testing (`mock: true`). |

---

## 3. Verified Demo Hotels

Use these proven properties for reliable live demonstrations:

| Hotel Name | Area | Supported Platforms | Verified Cohort | Typical Payables (1 Night, 2 Adults) | Spread |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bloomrooms City Centre** | Cunningham Road | Cleartrip, Booking.com | `(standard, 2, room_only, free)` | Cleartrip: ₹5,981<br>Booking.com: ₹5,580 | Booking.com ₹401 cheaper (7.2%) |
| **Radisson Blu Atria Bengaluru** | Palace Road | Cleartrip, Booking.com | `(deluxe, 2, room_only, free)` | Cleartrip: ₹11,077<br>Booking.com: ₹9,186 | Booking.com ₹1,891 cheaper (17.1%) |
| **La Marvella** | Jayanagar | Cleartrip, Booking.com | `(standard/deluxe, 2, breakfast, free)` | Cleartrip: ₹11,495 (flat promo package)<br>Booking.com: ₹13,499 | Cleartrip ₹2,004 cheaper (14.8%) |

---

## 4. 3-Pass Cohort Comparison Engine

TinyTravel enforces strict product comparability across three sequential passes:

```
Pass 1: Catalog Extraction
  ├── Cleartrip: parses all DOM rate cards (prices, room tier, meal, cancellation)
  └── Booking.com: JSON-first extraction from window.booking.env.b_rooms_available_and_soldout

Pass 2: Cohort Intersection
  ├── Standardizes 4-tuple: (room_tier, occupancy >= 2, meal_plan, cancellation_category)
  ├── Computes mathematical intersection: common_cohorts = ct_cohorts ∩ bk_cohorts
  └── If intersection is empty: outputs status="NOT COMPARABLE", reason="disjoint cohorts"

Pass 3: Coordinated Checkout
  ├── Selects cheapest intersecting cohort (preferring free cancellation)
  ├── Pins Cleartrip playbook to target button index
  ├── Pins Booking.com playbook to matching block ID
  └── Stops strictly at payment page; asserts fee_lines reconcile within 1%
```

---

## 5. Live Demo Execution Options

### Visual Headed Demonstration (Watch Browser Work)
To show the audience the browser navigating autonomously:
```powershell
py -3.11 scripts/run_3demo_hotels_matrix.py
```
Or execute a single verified pair:
```powershell
py -3.11 scripts/test_bloomrooms_pair.py
```

### Coverage & Reliability Dashboard Endpoint
Inspect live site capabilities, success rates, and blocker taxonomy:
```powershell
curl http://localhost:8000/api/coverage
```
Returns:
- `checkout_capable`: `true` for Cleartrip and Booking.com.
- `listing_capable`: `true` for Agoda and Google Hotels.
- `status`: `blocked` for Treebo/FabHotels (login/OTP gate) and MakeMyTrip (PerimeterX captcha).

---

## 6. Fallback Steps & Troubleshooting

1. **If Live Site Blocks or Throttles IP**:
   - Immediately switch backend to `DATA_MODE=saved` in `.env` or restart with:
     `$env:DATA_MODE="saved"; py -3.11 -m uvicorn main:app --port 8000`
   - Re-run search in web UI. It will serve the verified real run from `fixtures/saved_run.json`.
2. **Gemini Extraction Fallback**:
   - If a platform alters its checkout DOM structure, enable Gemini fallback extraction:
     `$env:GEMINI_FALLBACK_EXTRACTION="true"`
     `$env:GEMINI_API_KEY="<your-api-key>"`
   - TinyTravel will securely invoke Gemini to extract total payable and fee lines from raw page text.
3. **Sold Out Inventory**:
   - If a hotel is fully booked on the selected date, Booking.com returns `blocker="sold_out"`.
   - Switch date from Nov 20–21 to Nov 27–28 to restore available inventory.

---

## 7. Safety Invariants Enforced
- **Guest-Only**: Never logs in, never creates accounts, never enters OTP.
- **Dummy Data**: Name: `Test Guest`, Email: `test.guest+probe@example.com`, Phone: `9000000000`.
- **Payment Stop**: Always stops at the payment review page. Never clicks final pay/book.
- **Evidence-Backed**: Every price claim traces directly to a saved PNG screenshot in `results/recon/real_pairs/`.
