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
| **Saved Real Run** (Recommended for Demos) | `DATA_MODE=saved` | < 100 ms | No | Serves fully verified, real captured runs from `fixtures/saved_run.json` (`mock: false, saved: true`, $n=6$) with verbatim screenshots, room/bed types, and reconciled fee lines. Zero risk of live platform flakiness during presentations. |
| **Live Probing** | `DATA_MODE=live` | 10–25 s | Yes (Internet) | Spawns autonomous Playwright guest agents against Cleartrip and Booking.com, navigating in real-time and stopping strictly at the payment review page. |
| **Mock Development** | `DATA_MODE=mock` | < 50 ms | No | Synthetic test fixtures for rapid offline contract testing (`mock: true`). |

---

## 3. Verified Demo Hotels (Measured Payables, 2026-11-20)

Every price is 100% all-inclusive (base room + statutory GST + fees - discounts) and reconciled:

| Hotel Name | Area | Supported Platforms | Verified Cohort & Room | Cleartrip Payable | Booking.com Payable | Spread | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Bloomrooms City Centre** | Cunningham Road | Cleartrip, Booking.com | `Standard Twin Room` (2 Twin Beds, Room Only, Free Cancel) | ₹5,981.00 | ₹5,859.00 | ₹122.00 (2.04%) | **COMPARABLE** |
| **Radisson Blu Atria Bengaluru** | Palace Road | Cleartrip, Booking.com | `Superior Room` (1 King / Double, Room Only, Free Cancel) | ₹11,077.00 | ₹10,458.00 | ₹619.00 (5.59%) | **COMPARABLE** |
| **The Oberoi Bengaluru** | MG Road | Cleartrip, Booking.com | Cleartrip: `Superior Room`<br>Booking.com: `Luxury Room with Balcony` | ₹31,920.00 | ₹31,860.00 | ₹60.00 (0.19%) | **NOT COMPARABLE** (Room Name Mismatch) |
| **ibis Bengaluru City Centre** | Richmond Circle | Cleartrip, Booking.com | Cleartrip: `2 Twin Beds`<br>Booking.com: `1 Queen Bed` | ₹6,824.00 | ₹6,823.95 | ₹0.05 (0.00%) | **NOT COMPARABLE** (Bed Type Mismatch: Twin vs Queen) |

---

## 4. 3-Pass Cohort Comparison Engine

TinyTravel enforces strict product comparability across three sequential passes:

```
Pass 1: Catalog Extraction
  ├── Cleartrip: parses all DOM rate cards (prices, room tier, meal, cancellation)
  └── Booking.com: JSON-first extraction from window.booking.env.b_rooms_available_and_soldout

Pass 2: Cohort Intersection & Strict Product Matching
  ├── Standardizes 4-tuple: (room_tier, occupancy >= 2, meal_plan, cancellation_category)
  ├── Enforces room name & bed type equivalence (e.g., Twin vs Queen is flagged NOT COMPARABLE)
  ├── Computes mathematical intersection: common_cohorts = ct_cohorts ∩ bk_cohorts
  └── If intersection is empty: outputs status="NOT COMPARABLE", reason="disjoint cohorts"

Pass 3: Coordinated Checkout
  ├── Selects cheapest intersecting cohort (preferring free cancellation)
  ├── Pins Cleartrip playbook to target button index
  ├── Pins Booking.com playbook to matching block ID
  └── Stops strictly at payment page; asserts fee_lines sum to price_final_payable within 1%
```

---

## 5. Live Demonstration Script (Step-by-Step)

### Step 1: Instant Pitch & Dashboard Overview (30 seconds)
1. Set `DATA_MODE=saved` in `.env` and launch backend and web frontend.
2. Navigate to `http://localhost:3000`.
3. Show the UI rendering the **Measured Probed Run** ($n=6$, captured 2026-11-20).
4. Point out:
   - **Reconciliation Badge**: `ok` (100% exact match between fee lines and final payable).
   - **Verification Level**: `checkout` (Payment page reached; guest data only; zero login).
   - **Evidence Drawer**: Click screenshot to view verbatim payment page capture with date and rate highlighted.

### Step 2: Show Strict Room & Bed Comparability (1 minute)
1. Open the Comparison Matrix on the UI or query `GET /api/search/:id/results`.
2. Demonstrate **Bloomrooms City Centre**:
   - Cleartrip: Standard Twin Room, 2 Twin Beds.
   - Booking.com: Standard Twin Room, 2 Twin Beds.
   - Verdict: **COMPARABLE**. Real cross-site spread: ₹122.00 (2.04%).
3. Contrast with **ibis Bengaluru City Centre**:
   - Cleartrip: Twin Room, 2 Twin Beds.
   - Booking.com: Standard Queen Room, 1 Queen Bed.
   - Verdict: **NOT COMPARABLE** (`Bed type mismatch: 2 Twin Beds vs 1 Queen Bed`).
   - Highlight: Metasearch engines blindly compare these rates despite different room/bed amenities; TinyTravel detects the mismatch and refrains from false price comparison.

### Step 3: Show Real Tax Invariance & Coupon Mechanics (1 minute)
1. Click on **The Oberoi Bengaluru** fee breakdown:
   - Base Room: ₹28,000.00
   - Hotel Taxes (18% GST): ₹5,040.00
   - Cleartrip Cart Promo (`CTHOTEL`): -₹1,120.00
   - Final Payable: ₹31,920.00
2. Explain Coupon Analysis:
   - With CTHOTEL: Cleartrip ₹31,920.00 vs Booking.com ₹31,860.00 (Spread = ₹60 / 0.19%).
   - Without CTHOTEL: Cleartrip ₹33,040.00 vs Booking.com ₹31,860.00 (Spread = ₹1,180 / 3.70%).
   - Property Discounts (e.g. -₹704 on Bloomrooms) are available to 100% of guests automatically.

### Step 4: Autonomous Live Verification Run (Optional Headed Execution)
To demonstrate the live autonomous agent navigating in real-time:
```powershell
# Run a live back-to-back verification of Bloomrooms City Centre
py -3.11 scripts/run_paired_same_session.py
```
Observe the agent:
1. Navigate Cleartrip -> Select room -> Fill guest dummy info -> Reach payment review page -> Capture screenshot and fee lines.
2. Navigate Booking.com -> Select matching room -> Reach payment review page -> Capture full tax breakout.
3. Finish both within < 2 minutes total.

---

## 6. Coverage & Reliability Metrics

Inspect site capabilities, success rates, and blocker taxonomy via:
```powershell
curl http://localhost:8000/api/coverage
```
- **Cleartrip**: 100% checkout success rate on supported catalog hotels, median checkout latency: 22.4 s.
- **Booking.com**: 100% checkout success rate with full tax breakout, median checkout latency: 24.1 s.
- **Blocked Platforms**:
  - MakeMyTrip / Goibibo: PerimeterX anti-bot gate (`blocker: captcha`).
  - Treebo / FabHotels: Mandatory OTP/SMS phone auth wall (`blocker: otp` / `login`).
  - StayVista: Unsupported villa inventory structure (`blocker: other`).

---

## 7. Troubleshooting & Fallback Steps

| Issue | Root Cause | Fallback Action |
| :--- | :--- | :--- |
| Live checkout blocked by hotel inventory sold-out | Property has zero rooms left for target date | Script automatically tags `blocker="sold_out"` and falls back to alternate date (2026-11-27). |
| Booking.com query parameter stripping | Booking.com homepage redirect | Playwright handles search navigation session fallback automatically. |
| In-flight network disruption during presentation | Unstable conference WiFi | Switch immediately to `DATA_MODE=saved` to serve deterministic verified results without interruption. |
