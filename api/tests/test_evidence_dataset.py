"""
Tests for scripts/evidence_dataset.py

Verifies:
- Rejection of rows missing run_id or evidence_file
- Numeric parsing and fee line reconciliation
- Summary metrics: N, verified rate, median seconds, steps, cost, gap, cross-site spread
- Loading results/evidence_dataset.csv template
- CLI execution and JSON output
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.evidence_dataset import (
    calculate_evidence_metrics,
    check_reconciliation,
    load_evidence_csv,
    safe_float,
)


def test_safe_float_parsing():
    assert safe_float(100) == 100.0
    assert safe_float("150.50") == 150.50
    assert safe_float("₹1,234.50") == 1234.50
    assert safe_float("$99.99") == 99.99
    assert safe_float(None) == 0.0
    assert safe_float("") == 0.0
    assert safe_float("null") == 0.0


def test_check_reconciliation():
    is_ok, calc_val, diff = check_reconciliation(
        listed=1000, taxes=180, platform_fee=50, add_ons=0, discounts=0, final=1230
    )
    assert is_ok is True
    assert calc_val == 1230

    is_ok, _, _ = check_reconciliation(
        listed=1000, taxes=180, platform_fee=50, add_ons=0, discounts=0, final=1500
    )
    assert is_ok is False


def test_row_rejection_without_run_id_or_evidence_file(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(
        "stay_id,hotel_name,city,check_in,check_out,guests,platform,room_type,meal_plan,cancellation,"
        "listed_price,taxes,platform_fee,add_ons,discounts,final_payable,currency,timestamp,proof_url_or_hash,source,run_id,evidence_file,status\n"
        "S1,H1,BLR,2026-11-20,2026-11-21,2,cleartrip,Deluxe,room,free,1000,180,0,0,0,1180,INR,now,proof,tinyfish,,,\n"
        "S2,H2,BLR,2026-11-20,2026-11-21,2,agoda,Deluxe,room,free,1000,180,0,0,0,1180,INR,now,proof,tinyfish,RUN123,ev.json,verified\n",
        encoding="utf-8",
    )
    valid, rejected = load_evidence_csv(csv_file)
    assert len(valid) == 1
    assert len(rejected) == 1
    assert valid[0]["run_id"] == "RUN123"
    assert rejected[0]["rejection_reason"] == "Missing run_id or evidence_file"


def test_calculate_evidence_metrics_synthetic():
    rows = [
        {
            "stay_id": "STAY-1",
            "hotel_name": "Hotel Alpha",
            "platform": "cleartrip",
            "listed_price_num": 1000.0,
            "taxes_num": 180.0,
            "platform_fee_num": 50.0,
            "add_ons_num": 0.0,
            "discounts_num": 0.0,
            "final_payable_num": 1230.0,
            "status": "verified",
            "seconds": 150.0,
            "steps": 25,
            "cost_usd": 0.40,
        },
        {
            "stay_id": "STAY-1",
            "hotel_name": "Hotel Alpha",
            "platform": "agoda",
            "listed_price_num": 1100.0,
            "taxes_num": 198.0,
            "platform_fee_num": 0.0,
            "add_ons_num": 0.0,
            "discounts_num": 0.0,
            "final_payable_num": 1298.0,
            "status": "verified",
            "seconds": 200.0,
            "steps": 30,
            "cost_usd": 0.48,
        },
        {
            "stay_id": "STAY-2",
            "hotel_name": "Hotel Beta",
            "platform": "cleartrip",
            "listed_price_num": 2000.0,
            "taxes_num": 240.0,
            "platform_fee_num": 100.0,
            "add_ons_num": 0.0,
            "discounts_num": 0.0,
            "final_payable_num": 2340.0,
            "status": "blocked",
            "seconds": 30.0,
            "steps": 5,
            "cost_usd": 0.08,
        },
    ]

    metrics = calculate_evidence_metrics(rows)
    assert metrics["n_total"] == 3
    assert metrics["n_verified"] == 2
    assert metrics["verified_rates_per_platform"]["cleartrip"] == 50.0
    assert metrics["verified_rates_per_platform"]["agoda"] == 100.0
    assert metrics["median_steps"] == 25
    assert metrics["median_seconds"] == 150.0
    assert metrics["median_cost_usd"] == 0.40
    assert metrics["multi_site_stays_count"] == 1


def test_load_real_evidence_dataset_template():
    csv_path = REPO_ROOT / "results" / "evidence_dataset.csv"
    valid, rejected = load_evidence_csv(csv_path)
    assert len(valid) >= 1
    assert len(rejected) == 0
    row = valid[0]
    assert row["run_id"] == "b90d7c92-f7b0-4034-ad2e-9cee8b8a6771"
    assert row["status"] == "verified"
    assert row["is_reconciled"] is True


def test_cli_execution():
    csv_path = REPO_ROOT / "results" / "evidence_dataset.csv"
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "evidence_dataset.py"), str(csv_path), "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(res.stdout)
    assert "metrics" in data
    assert data["rejected_count"] == 0
