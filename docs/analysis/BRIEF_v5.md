# TinyTravel System & Empirical Benchmark Brief (v5)

> [!NOTE]
> Empirical benchmarks across all 25 executed live checkouts on disk, Batch 3 live run execution ($4.5920 spent, $6.3120 remaining), strict like-for-like comparability audit, and Startup Buildathon submission alignment. Strictly markdown tables only.

---

## 1. Measured vs. Estimated Figures (Batch 3 & Cumulative)

| Metric / Dimension | Category | Value | Basis / Evidence Reference / Run ID / URL |
| :--- | :---: | :---: | :--- |
| **Batch 3 Starting Wallet Balance** | **MEASURED** | **$10.9040 USD** | Queried via `c.wallet.get().available_balance` on `agent.tinyfish.ai`. |
| **Batch 3 Ending Wallet Balance** | **MEASURED** | **$6.3120 USD** | Queried via `c.wallet.get().available_balance` after run 8 checkpoint. |
| **Batch 3 Real Wallet Spend** | **MEASURED** | **$4.5920 USD** | Real wallet API delta across 8 executed live checkouts ($10.9040 - $6.3120). |
| **Batch 3 Checkpoint Early Stop** | **MEASURED** | **TRIGGERED** | Halting triggered at 8 runs: 3 / 8 verified (37.5% < 50.0% quality gate). |
| **Strict Like-for-Like Comparable Pairs** | **MEASURED** | **0 pairs (n=0)** | 0 of 9 hotel pairs matched room tier, guests, meal plan, AND cancellation terms. |
| **Recomputed Spread on Comparable Stays** | **MEASURED** | **N/A (n=0)** | Spread strictly uncomputed when room tier, guest count, or cancellation terms diverge. |
| **Total Real Checkouts in Benchmark CSV** | MEASURED | **20** | 1 baseline gate run + 10 Pack 1 live runs + 1 Batch 2 run + 8 Batch 3 runs ([evidence_dataset.csv](file:///e:/tinytravel/results/evidence_dataset.csv)). |
| **Verified Checkouts Count in Benchmark CSV** | MEASURED | **9 (45.0%)** | 1 baseline gate run + 5 Pack 1 live runs + 3 Batch 3 live runs. |
| **Verified Rate (Executed, Non-Sold-Out)** | **MEASURED** | **9 / 18 (50.0%)** | 9 verified out of 18 executed checkouts with active inventory (excl. 2 sold-out runs). |
| **Cleartrip Verified Rate (Non-Sold-Out)** | **MEASURED** | **6 / 10 (60.0%)** | 6 verified checkouts out of 10 non-sold-out runs on Cleartrip. |
| **Agoda Verified Rate (Non-Sold-Out)** | **MEASURED** | **3 / 8 (37.5%)** | 3 verified checkouts out of 8 non-sold-out runs on Agoda. |
| **Median Execution Time per Checkout** | MEASURED | **247.9 s** | Measured across all real checkouts in benchmark CSV ([evidence_dataset.csv](file:///e:/tinytravel/results/evidence_dataset.csv)). |
| **Median Autonomous Steps per Checkout** | MEASURED | **33.0 steps** | Measured across all real checkouts in benchmark CSV ([evidence_dataset.csv](file:///e:/tinytravel/results/evidence_dataset.csv)). |
| **Median Real Cost per Checkout** | **MEASURED** | **$0.5120 / run** | Derived from real wallet API deductions per checkout (range: $0.0000 to $1.5680). |
| **StartupBuildathon Pre-Built Code Clause** | **NOT FOUND** | **NOT FOUND** | No pre-built code restriction found on [startupbuildathon.com](https://startupbuildathon.com). |
| **StartupBuildathon Submission Format** | **QUOTED** | **5 Pillars** | *"Founder Profile, Product Potential, Market Viability, Technical Architecture, Use of Google AI & Cloud"* ([Source](https://startupbuildathon.com)). |
| **Own Agent Playwright Spike** | MEASURED | **0 / 5 (0.0%)** | [pack3_playwright_spike_results.json](file:///e:/tinytravel/results/pack3_playwright_spike_results.json) (Median 7.0s; blocked by Cleartrip dynamic SPA search input). |

---

## 2. Batch 3 Execution Log (8 Checkouts)

| # | Platform | Hotel Name | Status | Run ID | Time | Steps | Real Cost | Outcome / Breakdown |
| :---: | :--- | :--- | :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | Cleartrip | The Chancery Pavilion | `verified` | `0987a9fe-43c8` | 231.4s | 31 | $0.4960 | Payable: ₹5,250.00 (Base: ₹5,000 + Tax: ₹250). |
| **2** | Agoda | The Chancery Pavilion | `blocked` | `def0f993-efa5` | 600.0s | 44 | $0.0000 | Blocker: `timeout` (Agent timed out after 600s). |
| **3** | Cleartrip | The Pride Hotel | `blocked` | `a10d9e16-f8c7` | 508.7s | 62 | $1.5680 | Blocker: `other` (Hotel not listed on Cleartrip search). |
| **4** | Agoda | The Pride Hotel | `blocked` | `c7a5763a-81c1` | 281.2s | 35 | $0.5600 | Blocker: `other` (Hotel listed as "Pride Premier"). |
| **5** | Cleartrip | Radisson Blu Atria | `verified` | `341a9bef-7327` | 247.9s | 31 | $0.4960 | Listed: ₹9,387; Payable: ₹11,077 (+18.0% leak; free cancel). |
| **6** | Agoda | Radisson Blu Atria | `blocked` | `a4b51947-1c2b` | 266.8s | 34 | $0.5440 | Blocker: `other` (Stopped at traveller details step). |
| **7** | Cleartrip | Sterlings Mac Hotel | `unverified` | `a02fe19b-53c6` | 226.2s | 25 | $0.4000 | Occupancy mismatch (room fits 1 adult, requested 2). |
| **8** | Agoda | Sterlings Mac Hotel | `verified` | `e2434530-6d7d` | 234.3s | 33 | $0.5280 | Payable: ₹20,466.14 (Room standard, 2 adults, free cancel). |

---

## 3. Strict Like-for-Like Pair Comparability Audit

| Hotel Property | Cleartrip Offer & Terms | Agoda Offer & Terms | Status & Pricing Comparison | Strict Match Classification |
| :--- | :--- | :--- | :--- | :---: |
| **La Marvella** | `Executive Twin`, 3 ad, Breakfast, **non-refundable** | `Executive Twin`, 2 ad, Room only, **partial/free** | CT: ₹11,495.00 (`verified`)<br>AG: ₹15,175.27 (`verified`) | **NOT COMPARABLE**<br>(Guests, Meal, Cancel Diverge) |
| **Hotel City Centaur** | `>listing_page_text`, ₹1,341 (`blocked`) | `N/A`, null (`unverified`) | Both platforms had **zero inventory** for dates | **NOT COMPARABLE**<br>(Zero Inventory / Sold Out) |
| **Holiday Inn Whitefield** | `1 Queen Standard`, Breakfast, partial, ₹3,506 (`blocked`) | `1 Queen Accessible`, Breakfast, free, ₹3,434.50 (`verified`) | Cleartrip stopped at guest form; Agoda booked accessible | **NOT COMPARABLE**<br>(Tier, Cancel, Status Diverge) |
| **Taj Yeshwantpur** | `Superior City View Twin`, 2 adults, ₹17,228 (`verified`) | `Superior Twin Bed`, 1 adult listed, ₹15,505.20 (`unverified`) | Agoda selected single-occupancy card | **NOT COMPARABLE**<br>(Occupancy & Policy Diverge) |
| **Holiday Inn Racecourse**| `Standard Room Only`, partial, ₹10,729 (`verified`) | `1 Queen Turf View`, free cancel, ₹20,659.28 (`unverified`) | Agoda selected premium Turf View tier; split taxes | **NOT COMPARABLE**<br>(Tier, Policy, Status Diverge) |
| **The Chancery Pavilion** | `Superior Room`, 2 adults, Room Only, ₹5,250 (`verified`)| null (`blocked: timeout`) | Cleartrip verified; Agoda timed out at 600s | **NOT COMPARABLE**<br>(Status Diverge) |
| **The Pride Hotel** | null (`blocked: not found`) | null (`blocked: name mismatch`) | Property unavailable/mismatched on both portals | **NOT COMPARABLE** |
| **Radisson Blu Atria** | `Superior Room`, 2 ad, Room Only, free, ₹11,077 (`verified`) | `Superior Room`, 2 ad, Room Only, free, ₹11,210 (`blocked`) | Cleartrip verified; Agoda blocked before payment | **NOT COMPARABLE**<br>(Status Diverge) |
| **Sterlings Mac Hotel** | `Deluxe Suite`, 1 ad, Room Only, free, ₹38,869 (`unverified`) | `Room standard`, 2 ad, No meals, free, ₹20,466.14 (`verified`) | Cleartrip selected 1-ad suite; Agoda selected standard | **NOT COMPARABLE**<br>(Tier & Occupancy Diverge) |

### Strict Comparability Rule Evaluation
| Rule Requirement | Checked Criteria | Observed Match Status |
| :--- | :--- | :---: |
| **1. Room Tier Match** | Cleartrip and Agoda room name must describe identical category | 2 of 9 pairs matched tier |
| **2. Guest Count Match** | Booking summary must explicitly reflect 2 adults | 5 of 9 pairs matched guests |
| **3. Meal Plan Match** | Breakfast inclusion must be identical | 3 of 9 pairs matched meal plan |
| **4. Cancellation Match** | Cancellation policy terms must belong to same category | 3 of 9 pairs matched policy |
| **5. Both Verified** | Both checkouts must reach payment with fee reconciliation | 1 pair (La Marvella) verified on both |
| **Strict Like-for-Like (All 5 Match)** | All five criteria satisfied simultaneously | **0 pairs (n=0)** |
| **Spread on Comparable Stays** | Evaluated on strictly comparable pairs | **N/A (n=0)** |

---

## 4. Failure Analysis & Root Cause Classification

| Hotel & Platform | Observed Failure Mode | Classification | Root Cause Detail | Remediated Status |
| :--- | :--- | :---: | :--- | :---: |
| **Cleartrip — City Centaur** | Property displayed on listing but zero rooms available for 2 adults | `Site Flow` | Zero inventory for requested dates; cannot progress. | Discovery filter |
| **Agoda — City Centaur** | *"Sold out! Our last room is already booked"* displayed on search | `Site Flow` | Zero inventory for requested dates; no selectable card. | Discovery filter |
| **Cleartrip — Holiday Inn** | Reached traveller details with form filled; stopped before payment | `Agent Error` | Agent hit 33-step cap before clicking *"Continue to Payment"*. | Cap 40 + button rule |
| **Agoda — Taj Yeshwantpur** | Selected room card had *"1 adult"* text in booking summary | `Ambiguity` | Room defaulted to single occupancy; triggered rejection. | >= 2 adult card check |
| **Agoda — Holiday Inn** | *"Pay to Agoda: ₹18,530.72"* + *"Pay at hotel: ₹2,128.56"* split | `Site Flow` | Split payment model omitted hotel taxes from fee lines. | Split payment recon |
| **Agoda — Chancery Pavilion**| Autonomous session halted after 600s timeout on Agoda search | `Timeout` | Dynamic search grid pagination latency triggered 600s cap. | Open Investigation |
| **Cleartrip & Agoda — Pride**| Property not listed under exact query string on either platform | `Site Flow` | Portal uses alternative naming ("Pride Premier Bengaluru"). | Fuzzy hotel resolver |
| **Cleartrip — Sterlings Mac**| Cleartrip auto-assigned 1-adult room card on initial selection | `Ambiguity` | Selected room card had 1 adult capacity in summary. | Strict occupancy rule |
| **Agoda — Radisson Blu Atria** | Navigation paused on traveller details step before payment review | `Agent Error` | Multi-step form transition did not reach final review. | Form progression rule |

---

## 5. Wallet Accounting & Budget Tracking

| Accounting Line | Value | Currency | Basis / Verification Reference |
| :--- | :---: | :---: | :--- |
| **Prepaid Wallet (Before Batch 3)** | **$10.9040** | USD | Queried via `c.wallet.get().available_balance` on `agent.tinyfish.ai`. |
| **Prepaid Wallet (After Batch 3)** | **$6.3120** | USD | Queried via `c.wallet.get().available_balance` on `agent.tinyfish.ai`. |
| **Total Real Wallet Spend (Batch 3)**| **$4.5920** | USD | Deducted across 8 executed checkout attempts ($0.5740 average / run). |
| **Remaining Available Balance** | **$6.3120** | USD | Available in wallet for future probe executions. |
| **Total Lifetime Real Spend (All Probes)** | **$10.6240** | USD | Initial deposit depletion ($6.0320) + Batch 3 spend ($4.5920). |
