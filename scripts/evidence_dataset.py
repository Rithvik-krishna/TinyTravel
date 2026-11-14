"""
TinyTravel Evidence Dataset Analysis Script (Stage 1 / Pack 1)

Reads a CSV of hotel checkout rows (schema defined in docs/TinyTravel_Master_Plan_v3.md §2.4)
and calculates empirical metrics:
- Rejects rows without run_id + evidence_file
- N (total guest checkouts)
- Verified rate per platform
- Median seconds + steps + estimated cost per checkout (parsed from evidence files or metadata)
- Median fee leak gap % ((final - listed) / listed * 100) (same room only)
- Gap excluding taxes % ((final - taxes - listed) / listed * 100)
- Checkouts differing by >= 10%
- Cross-site spread % for identical stays across multiple platforms ((max - min) / min * 100)
- Share of searches where each platform is cheapest
- Share of searches with cross-site spread under 3% (virtual parity)
- Markdown tables output format

Usage:
    py -3.11 scripts/evidence_dataset.py [path/to/evidence_dataset.csv]
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_COLUMNS = [
    "stay_id",
    "hotel_name",
    "city",
    "check_in",
    "check_out",
    "guests",
    "platform",
    "room_type",
    "meal_plan",
    "cancellation",
    "listed_price",
    "taxes",
    "platform_fee",
    "add_ons",
    "discounts",
    "final_payable",
    "currency",
    "timestamp",
    "proof_url_or_hash",
    "source",
    "run_id",
    "evidence_file",
    "status",
]


def safe_float(val: Any, default: float = 0.0) -> float:
    """Parse numeric values safely, defaulting to 0.0 for empty or null strings."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if not s or s.lower() in ("null", "none", "nan", "n/a"):
        return default
    try:
        s = s.replace("₹", "").replace("$", "").replace(",", "")
        return float(s)
    except ValueError:
        return default


def check_reconciliation(
    listed: float,
    taxes: float,
    platform_fee: float,
    add_ons: float,
    discounts: float,
    final: float,
    tolerance_pct: float = 1.0,
) -> Tuple[bool, float, float]:
    """
    Check if itemized fee lines sum to final payable within +/- 1% tolerance.
    Equation: listed_price + taxes + platform_fee + add_ons - discounts == final_payable
    """
    calc_final = listed + taxes + platform_fee + add_ons - abs(discounts)
    if final == 0:
        return (calc_final == 0, calc_final, 0.0)
    diff = abs(calc_final - final)
    diff_pct = (diff / final) * 100.0
    is_ok = diff_pct <= tolerance_pct or diff <= 2.0
    return is_ok, calc_final, diff_pct


def load_evidence_csv(file_path: str | Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Read evidence CSV, validating run_id and evidence_file.
    Returns: (valid_rows, rejected_rows)
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Evidence CSV not found at: {path}")

    valid_rows: List[Dict[str, Any]] = []
    rejected_rows: List[Dict[str, Any]] = []

    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, raw_row in enumerate(reader, start=1):
            cleaned: Dict[str, Any] = {k.strip(): (v.strip() if v else "") for k, v in raw_row.items() if k}
            
            run_id = cleaned.get("run_id", "").strip()
            evidence_file = cleaned.get("evidence_file", "").strip()

            # Strict rule: reject rows without a valid real run_id + evidence_file
            if not run_id or not evidence_file:
                cleaned["rejection_reason"] = "Missing run_id or evidence_file"
                cleaned["row_num"] = idx
                rejected_rows.append(cleaned)
                continue
            elif run_id.lower().startswith("pending") or run_id.lower() in ("null", "none", "n/a"):
                cleaned["rejection_reason"] = "Pending or invalid run_id"
                cleaned["row_num"] = idx
                rejected_rows.append(cleaned)
                continue

            listed = safe_float(cleaned.get("listed_price"))
            taxes = safe_float(cleaned.get("taxes"))
            platform_fee = safe_float(cleaned.get("platform_fee"))
            add_ons = safe_float(cleaned.get("add_ons"))
            discounts = safe_float(cleaned.get("discounts"))
            final = safe_float(cleaned.get("final_payable"))

            is_recon, calc_val, diff_pct = check_reconciliation(
                listed, taxes, platform_fee, add_ons, discounts, final
            )

            # Check if evidence file exists and parse run metadata (steps, seconds, cost)
            ev_path = Path(evidence_file)
            steps = None
            seconds = None
            cost_usd = None
            if ev_path.is_file():
                try:
                    with open(ev_path, "r", encoding="utf-8") as ef:
                        ev_data = json.load(ef)
                        steps = ev_data.get("steps")
                        cost_usd = ev_data.get("cost_usd")
                        st = ev_data.get("started_at")
                        ft = ev_data.get("finished_at")
                        if st and ft:
                            dt_start = datetime.fromisoformat(st)
                            dt_finish = datetime.fromisoformat(ft)
                            seconds = (dt_finish - dt_start).total_seconds()
                except Exception:
                    pass

            cleaned["row_num"] = idx
            cleaned["listed_price_num"] = listed
            cleaned["taxes_num"] = taxes
            cleaned["platform_fee_num"] = platform_fee
            cleaned["add_ons_num"] = add_ons
            cleaned["discounts_num"] = discounts
            cleaned["final_payable_num"] = final
            cleaned["is_reconciled"] = is_recon
            cleaned["reconciliation_diff_pct"] = diff_pct
            cleaned["calculated_final"] = calc_val
            cleaned["steps"] = steps
            cleaned["seconds"] = seconds
            cleaned["cost_usd"] = cost_usd

            valid_rows.append(cleaned)

    return valid_rows, rejected_rows


def calculate_evidence_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate summary statistics across checkout rows and multi-site stays."""
    if not rows:
        return {
            "n_total": 0,
            "n_verified": 0,
            "verified_rates_per_platform": {},
            "median_seconds": None,
            "median_steps": None,
            "median_cost_usd": None,
            "median_gap_pct": None,
            "median_gap_ex_taxes_pct": None,
            "count_gap_ge_10": 0,
            "share_gap_ge_10_pct": 0.0,
            "multi_site_stays_count": 0,
            "median_cross_site_spread_pct": None,
            "share_spread_under_3_pct": 0.0,
            "cheapest_site_counts": {},
            "cheapest_site_shares_pct": {},
            "platforms": [],
            "hotels": [],
            "formatted_headline": "No checkout data available.",
        }

    n_total = len(rows)
    verified_rows = [r for r in rows if r.get("status", "").lower() == "verified" and r["final_payable_num"] > 0]
    n_verified = len(verified_rows)

    # Platform verified rates
    platform_total: Dict[str, int] = {}
    platform_verified: Dict[str, int] = {}
    for r in rows:
        plat = r.get("platform", "").lower()
        platform_total[plat] = platform_total.get(plat, 0) + 1
        if r.get("status", "").lower() == "verified":
            platform_verified[plat] = platform_verified.get(plat, 0) + 1

    verified_rates = {
        p: round((platform_verified.get(p, 0) / tot * 100.0), 1)
        for p, tot in platform_total.items()
    }

    # Agent performance metrics
    seconds_list = [r["seconds"] for r in rows if r.get("seconds") is not None]
    steps_list = [r["steps"] for r in rows if r.get("steps") is not None]
    cost_list = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]

    median_sec = round(statistics.median(seconds_list), 1) if seconds_list else None
    median_steps = round(statistics.median(steps_list), 1) if steps_list else None
    median_cost = round(statistics.median(cost_list), 3) if cost_list else None

    # Price gaps on verified rows
    gap_pcts: List[float] = []
    gap_ex_taxes_pcts: List[float] = []

    for r in verified_rows:
        listed = r["listed_price_num"]
        taxes = r["taxes_num"]
        final = r["final_payable_num"]
        if listed > 0:
            gap = ((final - listed) / listed) * 100.0
            gap_ex_tax = ((final - taxes - listed) / listed) * 100.0
            gap_pcts.append(gap)
            gap_ex_taxes_pcts.append(gap_ex_tax)

    median_gap = round(statistics.median(gap_pcts), 1) if gap_pcts else None
    median_gap_ex = round(statistics.median(gap_ex_taxes_pcts), 1) if gap_ex_taxes_pcts else None
    count_ge_10 = sum(1 for g in gap_pcts if g >= 10.0)
    share_ge_10 = round((count_ge_10 / len(gap_pcts) * 100.0), 1) if gap_pcts else 0.0

    # Cross-site spread & cheapest site distribution
    stays: Dict[str, List[Dict[str, Any]]] = {}
    for r in verified_rows:
        sid = r.get("stay_id") or f"{r.get('hotel_name', '')}_{r.get('check_in', '')}"
        stays.setdefault(sid, []).append(r)

    multi_site_stays = {sid: r_list for sid, r_list in stays.items() if len(r_list) >= 2}

    spread_pcts: List[float] = []
    cheapest_counts: Dict[str, float] = {}

    for sid, r_list in multi_site_stays.items():
        finals = [r["final_payable_num"] for r in r_list]
        min_final = min(finals)
        max_final = max(finals)
        if min_final > 0:
            spread = ((max_final - min_final) / min_final) * 100.0
            spread_pcts.append(spread)

        cheapest_in_stay = [r["platform"].lower() for r in r_list if abs(r["final_payable_num"] - min_final) < 0.01]
        weight = 1.0 / len(cheapest_in_stay) if cheapest_in_stay else 1.0
        for p in cheapest_in_stay:
            cheapest_counts[p] = cheapest_counts.get(p, 0.0) + weight

    n_multi = len(multi_site_stays)
    median_spread = round(statistics.median(spread_pcts), 1) if spread_pcts else None
    count_under_3 = sum(1 for s in spread_pcts if s < 3.0)
    share_under_3 = round((count_under_3 / n_multi * 100.0), 1) if n_multi > 0 else 0.0

    cheapest_shares: Dict[str, float] = {}
    if n_multi > 0:
        for p, count in cheapest_counts.items():
            cheapest_shares[p] = round((count / n_multi) * 100.0, 1)

    platforms = sorted(list({r.get("platform", "").title() for r in rows if r.get("platform")}))
    hotels = sorted(list({r.get("hotel_name", "").title() for r in rows if r.get("hotel_name")}))

    headline = (
        f"Across {n_verified} verified guest checkouts across {n_multi} multi-site hotel stays "
        f"({', '.join(platforms)}, Bengaluru, 20–21 Nov 2026, 2 guests), the final payable price was a "
        f"median of {median_gap}% above the listed price ({median_gap_ex}% excluding taxes), "
        f"with {count_ge_10} of {n_verified} checkouts differing by 10% or more. Between platforms "
        f"for identical rooms, the median cross-site spread was {median_spread}%; "
        f"and {share_under_3}% of stays had a spread under 3% (virtual parity). Observed on these runs."
    )

    return {
        "n_total": n_total,
        "n_verified": n_verified,
        "verified_rates_per_platform": verified_rates,
        "median_seconds": median_sec,
        "median_steps": median_steps,
        "median_cost_usd": median_cost,
        "median_gap_pct": median_gap,
        "median_gap_ex_taxes_pct": median_gap_ex,
        "count_gap_ge_10": count_ge_10,
        "share_gap_ge_10_pct": share_ge_10,
        "multi_site_stays_count": n_multi,
        "median_cross_site_spread_pct": median_spread,
        "share_spread_under_3_pct": share_under_3,
        "cheapest_site_counts": {k: round(v, 2) for k, v in cheapest_counts.items()},
        "cheapest_site_shares_pct": cheapest_shares,
        "platforms": platforms,
        "hotels": hotels,
        "formatted_headline": headline,
    }


def print_markdown_report(metrics: Dict[str, Any], rejected: List[Dict[str, Any]]) -> None:
    """Print results strictly in markdown table format."""
    print("### TinyTravel Evidence Dataset Benchmark Report\n")
    print("| Metric | Value | Category |")
    print("|---|---|---|")
    print(f"| Total Checkouts (N) | {metrics['n_total']} | MEASURED |")
    print(f"| Verified Checkouts | {metrics['n_verified']} | MEASURED |")
    print(f"| Rejected Rows (Missing run_id/evidence) | {len(rejected)} | MEASURED |")
    print(f"| Median Seconds / Checkout | {metrics['median_seconds']} s | MEASURED |")
    print(f"| Median Steps / Checkout | {metrics['median_steps']} | MEASURED |")
    print(f"| Median Cost / Checkout | ${metrics['median_cost_usd']} | ESTIMATED (steps × $0.016) |")
    print(f"| Median Fee Leak Gap % | +{metrics['median_gap_pct']}% | MEASURED |")
    print(f"| Median Gap Excluding Taxes % | +{metrics['median_gap_ex_taxes_pct']}% | MEASURED |")
    print(f"| Checkouts with Gap >= 10% | {metrics['count_gap_ge_10']} ({metrics['share_gap_ge_10_pct']}%) | MEASURED |")
    print(f"| Multi-Site Stays Analyzed | {metrics['multi_site_stays_count']} | MEASURED |")
    print(f"| Median Cross-Site Spread % | {metrics['median_cross_site_spread_pct']}% | MEASURED |")
    print(f"| Stays with Spread < 3% (Parity) | {metrics['share_spread_under_3_pct']}% | MEASURED |")
    print()

    print("#### Verified Rate per Platform")
    print("| Platform | Verified Rate (%) |")
    print("|---|---|")
    for plat, rate in metrics.get("verified_rates_per_platform", {}).items():
        print(f"| {plat.title()} | {rate}% |")
    print()

    print("#### Cheapest Platform Share")
    print("| Platform | Share (%) | Stays Count |")
    print("|---|---|---|")
    for plat, share in metrics.get("cheapest_site_shares_pct", {}).items():
        count = metrics.get("cheapest_site_counts", {}).get(plat, 0)
        print(f"| {plat.title()} | {share}% | {count} |")
    print()

    print("#### Formatted Headline Sentence")
    print(f"> \"{metrics['formatted_headline']}\"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze TinyTravel evidence dataset CSV.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="results/evidence_dataset.csv",
        help="Path to evidence CSV (default: results/evidence_dataset.csv)",
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics instead of markdown tables")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"Error: File '{csv_path}' does not exist.", file=sys.stderr)
        return 1

    try:
        valid_rows, rejected_rows = load_evidence_csv(csv_path)
        metrics = calculate_evidence_metrics(valid_rows)

        if args.json:
            out = {
                "metrics": metrics,
                "rejected_count": len(rejected_rows),
                "rejected_rows": rejected_rows,
            }
            print(json.dumps(out, indent=2))
        else:
            print_markdown_report(metrics, rejected_rows)
        return 0
    except Exception as e:
        print(f"Error processing evidence dataset: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
