# Provenance Audit: fixtures/saved_run.json

Every field in `fixtures/saved_run.json` has been audited against the primary run file `results/3demo_hotels_matrix_results.json` to eliminate invented values.

## 1. Directly From Run File (`results/3demo_hotels_matrix_results.json`)
The following core pricing, booking, and evidence fields originate directly from the Playwright browser run logs:

| Field Path | Source Run Property | Real Observed Value in `fixtures/saved_run.json` |
| :--- | :--- | :--- |
| `offers[0].hotel_name` | `hotel` | `"Bloomrooms City Centre"` |
| `offers[0].site` | `site` | `"Cleartrip"` |
| `offers[0].price_final_payable` | `payable` | `₹5,981.00` |
| `offers[0].fee_lines` | `fee_lines` | `[Room: 6400, Tax: 285, Discount: -704, Fee: 0]` |
| `offers[0].room_type` | `room_type` | `"Room Only"` |
| `offers[0].cancellation_policy` | `cancellation_policy` | `"Free cancellation till 18 Nov"` |
| `offers[0].reached_payment_page` | `reached_payment` | `true` |
| `offers[0].evidence[0].url` | `evidence` | `"/results/recon/real_pairs/cleartrip_bloomrooms_city_centre.png"` |
| `offers[1].hotel_name` | `hotel` | `"Bloomrooms City Centre"` |
| `offers[1].site` | `site` | `"Booking.com"` |
| `offers[1].price_final_payable` | `payable` | `₹5,760.00` |
| `offers[1].fee_lines` | `fee_lines` | `[Total room rate (incl. taxes): 5760.0]` |
| `offers[1].room_type` | `room_type` | `"Standard Double Room"` |
| `offers[1].evidence[0].url` | `evidence` | `"/results/recon/real_pairs/bookingcom_bloomrooms_city_centre_2026-11-20_1794766445.png"` |
| `offers[2].price_final_payable` | `payable` | `₹11,077.00` (Radisson Cleartrip) |
| `offers[3].price_final_payable` | `payable` | `₹9,500.00` (Radisson Booking.com) |
| `offers[4].price_final_payable` | `payable` | `₹11,495.00` (La Marvella Cleartrip) |
| `offers[5].price_final_payable` | `payable` | `₹15,299.10` (La Marvella Booking.com) |

---

## 2. Removed Fields (Invented Numbers Eliminated)
- **`offers[].transparency`**: **REMOVED**. The previous mock/dummy transparency score (`9.4`, breakdown `10.0`, `9.5`) was synthetic and not parsed from page DOM. Since `transparency` is optional in the `Offer` schema, it has been eliminated entirely.
- **`offers[].price_trail`**: Sanitized. The synthetic `listing` price step was removed; `price_trail` now only logs the verified `payment` step amount.
- **`summary_strip.avg_fee_leak_pct`**: Reset from previous synthetic `4.2%` to `0.0%` (direct average of verified offers).

---

## 3. Contract Scaffolding & Derived Fields (Labeled)
These fields are required by the Pydantic API contract (`ResultsResponse`) for UI rendering:

| Field Path | Category | Reason / Formula |
| :--- | :--- | :--- |
| `search_request` | Contract Scaffolding | Query parameters (`Bengaluru, 20-21 Nov 2026, 2 guests`) that produced the run. |
| `travel_profile` | Contract Scaffolding | User intent constraints (`deal_mode: best_value`, `prefers_refundable: true`). |
| `hotels[].area`, `rating` | Contract Scaffolding | Static city/neighborhood directory metadata. |
| `hotel_groups` | Derived Post-Run | Canonical entity clustering (`match_status: merged` for Bloomrooms, `suggested` for Radisson & La Marvella). Labeled `[DERIVED POST-RUN]`. |
| `handoff` | Contract Scaffolding | Handoff payload for the cheapest verified offer (`h1_bookingcom`) with guest test contact. Labeled `[CONTRACT SCAFFOLDING]`. |
| `summary_strip` | Derived Post-Run | Computed directly from offers: `verified: 6`, `unverified: 0`, `blocked: 0`. |
| `verdicts.non_comparable_warnings`| Derived Post-Run | Exact warnings produced by the 3-pass cohort engine: Radisson Blu Atria (standard vs deluxe) and La Marvella (standard vs executive). |
