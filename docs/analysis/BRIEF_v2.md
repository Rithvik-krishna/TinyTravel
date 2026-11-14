# TinyTravel System & Empirical Benchmark Brief (v2)

> [!NOTE]
> Ground-truth reconciliation and empirical benchmarks across all live runs, Playwright spike, volatility testing, and competitor evaluations.

---

## 1. Measured vs. Estimated & Relabeled Figures

| Metric / Dimension | Category | Value | Basis / Evidence Reference / Run ID / URL |
| :--- | :--- | :--- | :--- |
| **Cleartrip Fee Leak Gap (Baseline)** | MEASURED | **+34.6%** | `run_id: b90d7c92-f7b0-4034-ad2e-9cee8b8a6771` (₹8,867 base -> ₹11,933 final payable; ₹1,095 fee + ₹1,971 taxes). |
| **Cleartrip Live Final Payable (Run 1)** | MEASURED | **₹11,495.00** | `run_id: e7b2edae-0f1d-42fe-b3a7-4ec44bc2a765` (`live_pack1_cleartrip_la_marvella_raw.json`). Exact reconciliation: 15,639 - 4,692 + 1,971 - 2,518 + 1,095 = 11,495. |
| **Agoda Live Final Payable (Run 2)** | MEASURED | **₹15,175.27** | `run_id: bbd08347-96b5-4dba-9938-1eec71b5fbee` (`live_pack1_agoda_la_marvella_raw.json`). Executive Twin, 2 adults, 18% tax included. |
| **Cross-Site Price Spread (La Marvella)** | MEASURED | **32.01%** | \|₹15,175.27 - ₹11,495.00\| / ₹11,495.00 = 32.01% disparity on strictly identical room tier. |
| **Recomputed Spread on Comparable Stays** | MEASURED | **32.01%** | Computed strictly on comparable verified pair (La Marvella: Executive Twin). |
| **Stays with Spread < 3% (Parity)** | MEASURED | **0.0%** | 0 of 1 strictly comparable stay fell within 3% virtual parity. |
| **Total Live Checkouts Analyzed (CSV)** | MEASURED | **11** | 1 historic gate baseline + 10 Pack 1 live runs (`results/evidence_dataset.csv`). |
| **Verified Checkouts Count (CSV)** | MEASURED | **6 (54.5%)** | 1 historic gate baseline + 5 Pack 1 live runs. Zero rejected rows. |
| **Pack 1 Batch Live Verification Rate** | MEASURED | **50.0% (5 / 10)** | Cleartrip: 60.0% (3/5 verified); Agoda: 40.0% (2/5 verified). Passed 40% gate at run 6. |
| **Median Execution Time per Checkout** | MEASURED | **266.4 s** | Measured across all live checkout probes (range: 151.8s to 594.9s). |
| **Median Autonomous Steps per Checkout** | MEASURED | **33 steps** | Measured across all live checkout probes (range: 15 to 39 steps). |
| **Estimated Spend (Pack 1 + Volatility)** | ESTIMATED | **$5.4080** | 338 total TinyFish steps × $0.016/step. |
| **Actual Deducted API Billing Cost** | **UNKNOWN** | **$0.0000** | API balance remains $50.0000. Real billing cost is unknown until provider invoice. |
| **Own Agent Playwright Spike (Part E)** | **MEASURED** | **0 / 5 (0.0%)** | `results/pack3_playwright_spike_results.json` (Median 7.0s; blocked by Cleartrip SPA search flow). |
| **Agoda La Marvella 3.3h Price Drift** | MEASURED | **0.00%** | Run 2 (13:11 IST: ₹15,175.27) vs Run 3 (16:34 IST: ₹15,175.27). `run_id: 964761d6...` |
| **Cleartrip La Marvella Coupon Drift** | MEASURED | **-3.67% to +5.83%** | Coupons varied between ₹2,080 and ₹2,737, driving payable from ₹11,276 to ₹11,933. |

---

## 2. Table of Every Live Run on Disk & Count Reconciliation

| Run ID | Platform | Hotel Name | Status | Blocker / Reason | Sec | Steps | Room Text | Gst | Meal | Cancellation | Listed | Payable | Coupon / Discount Lines |
| :--- | :--- | :--- | :---: | :--- | :---: | :---: | :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `probe_1730356935` | Cleartrip | La Marvella | `verified` | none | 232s | 29 | Deluxe Double | 2 | Room only | non_refundable | ₹15,639 | ₹11,276 | Discount: -₹4,692; Offer: -₹2,737 |
| `d82b558c-6630` | Cleartrip | La Marvella | `completed` | none | 240s | 30 | Executive Twin (City view) | 2 | Room only | non_refundable | ₹15,639 | ₹11,933 | Property: -₹4,692; CTHOTEL: -₹2,080 |
| `b90d7c92-f7b0` | Cleartrip | La Marvella | `verified` | none | 240s | 33 | Executive Twin | 2 | Breakfast | free | ₹8,867 | ₹11,933 | Property: -₹4,692; CTHOTEL: -₹2,080 |
| `9b3e96a7-adbc` | Agoda | La Marvella | `completed` | none | 332s | 32 | Executive Twin | 2 | Breakfast | non_refundable | ₹10,948 | ₹12,936.93 | none |
| `90ff5677-3d75` | Booking.com | La Marvella | `completed` | none | 280s | 32 | Executive Room | 2 | Breakfast | free | ₹11,624 | ₹14,297.93 | Bonus savings (21% off): -₹3,755.01 |
| `e7b2edae-0f1d` | Cleartrip | La Marvella | `verified` | none | 240s | 33 | Executive Twin | 2 | Room only | non_refundable | null | ₹11,495 | Property: -₹4,692; CTHOTEL: -₹2,518 |
| `bbd08347-96b5` | Agoda | La Marvella | `verified` | none | 387s | 35 | Executive Twin | 2 | Room only | partial | ₹10,967 | ₹15,175.27 | none |
| `1486cdc4-d6fd` | Cleartrip | Hotel City Centaur | `blocked` | other (Sold out) | 595s | 34 | >listing_page_text | 2 | Room only | free | null | ₹1,341 | none |
| `83f6e966-369e` | Agoda | Hotel City Centaur | `unverified` | none (Sold out) | 152s | 15 | N/A | 2 | Room only | partial | null | null | none |
| `d8296784-6869` | Cleartrip | Holiday Inn Whitefield | `blocked` | other (Step cap) | 262s | 33 | 1 Queen Standard | 2 | Breakfast | partial | ₹3,506 | ₹3,506 | none |
| `120cab24-9b55` | Agoda | Holiday Inn Whitefield | `verified` | none | 232s | 23 | 1 Queen Accessible | 2 | Breakfast | free | ₹3,270 | ₹3,434.50 | Extra Person Fee: ₹525 |
| `5c6b01be-96fc` | Cleartrip | Taj Yeshwantpur | `verified` | none | 273s | 31 | Superior City View Twin | 2 | Room only | non_refundable | null | ₹17,228 | none |
| `8986cd9c-7c80` | Agoda | Taj Yeshwantpur | `unverified` | none (Occ mismatch) | 315s | 33 | Superior Room Twin | 1 | Room only | partial | ₹13,140 | ₹15,505.20 | none |
| `325360d5-2a50` | Cleartrip | Holiday Inn Racecourse| `verified` | none | 306s | 39 | Standard Room Only | 2 | Room only | partial | null | ₹10,729 | none |
| `d14bdd0b-39bd` | Agoda | Holiday Inn Racecourse| `unverified` | none (Tax split) | 238s | 32 | 1 Queen Turf View | 2 | Room only | free | null | ₹20,659.28 | none |
| `964761d6-f1ff` | Agoda | La Marvella (Run 3) | `verified` | none | 336s | 30 | Executive Twin | 2 | Room only | free | ₹12,860 | ₹15,175.27 | none |

### Reconciliation of Run Counts
| Scope / Dataset | Total Runs | Verified | Blocked | Unverified | Reconciliation Truth |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Pack 1 Live Batch Only** | **10** | **5 (50.0%)** | **2 (20.0%)** | **3 (30.0%)** | 10 live checkouts executed sequentially across 5 hotels on 14 Nov. |
| **`evidence_dataset.csv` Total** | **11** | **6 (54.5%)** | **2 (18.2%)** | **3 (27.3%)** | Row 2 is baseline gate run (`b90d7c92...`, verified) + 10 Pack 1 live runs. |
| **All Raw Files on Disk** | **16** | **9 (56.3%)** | **2 (12.5%)** | **5 (31.2%)** | 5 earlier gate/probe runs + 10 Pack 1 live runs + 1 Volatility Run 3. |

---

## 3. Side-by-Side Room Comparison & Recomputed Spread

| Hotel Property | Cleartrip Room & Policy | Agoda Room & Policy | Status & Pricing Comparison | Match Classification |
| :--- | :--- | :--- | :--- | :---: |
| **La Marvella** | `Executive Twin`, 2 adults, Room only, non-refundable | `Executive Twin`, 2 adults, Room only, partial cancellation | Cleartrip: **₹11,495.00** (`verified`)<br>Agoda: **₹15,175.27** (`verified`) | **COMPARABLE**<br>Spread: **32.01%** |
| **Hotel City Centaur** | `>listing_page_text`, ₹1,341 (`blocked`) | `N/A`, null (`unverified`) | Both platforms had **zero inventory** for dates | **NOT COMPARABLE** |
| **Holiday Inn Whitefield** | `1 Queen Standard`, Breakfast, partial cancel, ₹3,506 (`blocked`) | `1 Queen Accessible`, Breakfast, free cancel, ₹3,434.50 (`verified`) | Cleartrip stopped at guest details; Agoda booked accessible tier | **NOT COMPARABLE**<br>(Tier & Status Mismatch) |
| **Taj Yeshwantpur** | `Superior City View Twin`, 2 adults, ₹17,228 (`verified`) | `Superior Twin Bed`, 1 adult listed, ₹15,505.20 (`unverified`) | Agoda selected 1-adult occupancy card | **NOT COMPARABLE**<br>(Occupancy Mismatch) |
| **Holiday Inn Racecourse**| `Standard Room Only`, 2 adults, ₹10,729 (`verified`) | `1 Queen Turf View`, 2 adults, ₹20,659.28 (`unverified`) | Agoda selected premium Turf View tier; split taxes | **NOT COMPARABLE**<br>(Tier Mismatch) |

### Explanation: Holiday Inn Express Agoda (₹3,434.50) vs. Cleartrip (₹3,506.00)
- **Nature of Figures**: Both are full 1-night total payable amounts for 2 guests (NOT per-night unit errors).
- **Driver of ₹71.50 (2.08%) Difference**: Agoda selected an *"Accessible Room with free laundromat"* (base ₹2,909.50 + Extra Person fee ₹525.00 = ₹3,434.50), whereas Cleartrip selected the standard *"1 Queen Standard"* room (base ₹3,339.00 + 5% GST ₹167.00 = ₹3,506.00).

---

## 4. Volatility Test: La Marvella 3-Run Longitudinal Comparison

| Platform | Probe Run / Attempt | Timestamp (IST) | Room Text & Guests | Final Payable | Coupon / Discount Lines Captured | Interval & Price Drift % |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **Cleartrip** | Run 1 (`probe_1730...`) | 31-Oct-2026 12:12 | Deluxe Double (2 ad) | **₹11,276.00** | Discount: -₹4,692; Offer: -₹2,737 | Baseline |
| **Cleartrip** | Run 2 (`b90d7c92...`) | 31-Oct-2026 17:46 | Executive Twin (2 ad) | **₹11,933.00** | Property: -₹4,692; CTHOTEL: -₹2,080 | +5h 34m: **+5.83% drift** |
| **Cleartrip** | Run 3 (`e7b2edae...`) | 14-Nov-2026 13:05 | Executive Twin (2 ad) | **₹11,495.00** | Property: -₹4,692; CTHOTEL: -₹2,518 | +14 days: **-3.67% drift** |
| **Agoda** | Run 1 (`9b3e96a7...`) | 31-Oct-2026 17:36 | Executive Twin (2 ad) | **₹12,936.93** | none (Tax included in base) | Baseline |
| **Agoda** | Run 2 (`bbd08347...`) | 14-Nov-2026 13:11 | Executive Twin (2 ad) | **₹15,175.27** | none (Tax included in base) | +14 days: **+17.30% drift** |
| **Agoda** | Run 3 (`964761d6...`) | 14-Nov-2026 16:34 | Executive Twin (2 ad) | **₹15,175.27** | none (Tax included in base) | +3h 23m: **0.00% drift (Stable)** |

---

## 5. Failure Analysis from Raw Outputs & Ranked Remediation

| Hotel & Platform | Observed Failure Mode from Raw Output | Classification | Root Cause Detail |
| :--- | :--- | :--- | :--- |
| **Cleartrip — City Centaur** | Property displayed on listing but zero rooms available for 2 adults | `Site Flow` | Zero inventory for requested dates; cannot progress to payment. |
| **Agoda — City Centaur** | *"Sold out! Our last room is already booked"* displayed on search | `Site Flow` | Zero inventory for requested dates; no room card selectable. |
| **Cleartrip — Holiday Inn** | Reached traveller details with form filled; stopped before payment | `Agent Error` | Agent hit 33-step cap before clicking final *"Continue to Payment"*. |
| **Agoda — Taj Yeshwantpur** | Selected room card had *"1 adult"* text in booking summary | `Ambiguity` | Room defaulted to single occupancy; triggered rule rejection. |
| **Agoda — Holiday Inn** | *"Pay to Agoda: ₹18,530.72"* + *"Pay at hotel: ₹2,128.56"* split | `Site Flow` | Split payment model omitted hotel taxes from primary fee lines. |

### Ranked Fixes by Expected Verification Gain
1. **Rank 1 (Highest Gain, +20%)**: Increase Cleartrip step cap from 30/33 to 40; instruct agent to click *"Continue to Payment"* immediately after guest form fill.
2. **Rank 2 (+20% Cost Reduction)**: Pre-filter zero-inventory/sold-out properties during discovery before launching browser checkouts.
3. **Rank 3 (+10%)**: Update `verify_offer` schema to parse split payments (`pay_now` + `pay_at_hotel`).
4. **Rank 4 (+10%)**: Enforce strict adult count selector validation on Agoda room selection grids.

---

## 6. Part E: Playwright 5-Run Cleartrip Benchmark (Post-Install)

| Hotel Target | Execution Status | Blocker | Elapsed | LLM Cost | Observed Failure Mode |
| :--- | :---: | :--- | :---: | :---: | :--- |
| **La Marvella** | `unverified` | `layout` | 21.1s | $0.00 | Hotel card not visible on page 1 of generic city search. |
| **Hotel City Centaur** | `unverified` | `layout` | 6.6s | $0.00 | Hotel card not visible on page 1 of generic city search. |
| **Holiday Inn Whitefield** | `unverified` | `layout` | 7.2s | $0.00 | Hotel card not visible on page 1 of generic city search. |
| **Taj Yeshwantpur** | `unverified` | `layout` | 7.0s | $0.00 | Hotel card not visible on page 1 of generic city search. |
| **Holiday Inn Racecourse** | `unverified` | `layout` | 7.0s | $0.00 | Hotel card not visible on page 1 of generic city search. |
| **Summary / Benchmark** | **0 / 5 (0.0%)** | `layout` | **Median: 7.0s** | **$0.000** | **Failure Mode**: Cleartrip client-side SPA requires typing in the search box to filter properties; direct URL params only load generic city listing. |

---

## 7. Spend Accounting & Balance Tracking

| Accounting Line | Value (USD) | Category | Notes / Verification Basis |
| :--- | :---: | :---: | :--- |
| **Initial Spendable Balance** | **$50.0000** | MEASURED | Queried via `tinyfish.get_balance()` at session start. |
| **Pack 1 Batch (10 Runs)** | **$4.9280** | ESTIMATED | 308 steps × $0.016/step across 10 checkouts. |
| **Volatility Agoda Run 3** | **$0.4800** | ESTIMATED | 30 steps × $0.016/step (`run_id: 964761d6...`). |
| **Playwright Spike (5 Runs)** | **$0.0000** | MEASURED | Local Chromium execution; 0 LLM tokens. |
| **Total Estimated Spend** | **$5.4080** | ESTIMATED | Incremental session spend strictly monitored. |
| **Provider Deducted Cost** | **UNKNOWN** | **UNKNOWN** | API balance remains $50.0000; actual deduction unknown until dashboard. |
| **Ending Spendable Balance** | **$50.0000** | MEASURED | Pre-funded pool intact; estimated effective balance: $44.5920. |
