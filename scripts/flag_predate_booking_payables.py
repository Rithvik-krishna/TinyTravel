import json
from pathlib import Path

def audit_booking_payables():
    results_dir = Path("results")
    audit = []

    # 1. 3demo_hotels_matrix_results.json
    f1 = results_dir / "3demo_hotels_matrix_results.json"
    if f1.exists():
        data = json.loads(f1.read_text(encoding="utf-8"))
        for idx, entry in enumerate(data):
            bk = entry.get("bookingcom", {})
            audit.append({
                "source_file": "results/3demo_hotels_matrix_results.json",
                "entry_index": idx,
                "hotel_name": entry.get("hotel_name"),
                "check_in": entry.get("check_in"),
                "status": "FLAGGED_PREDATES_FIX" if bk.get("reached_payment") else "BLOCKED_SOLD_OUT",
                "payable": bk.get("payable"),
                "fallback_risk": "High (contained fallback regex/tax multiplier logic)",
                "reproduced_post_fix": None,
            })

    # 2. bookingcom_additional_checkouts.json
    f2 = results_dir / "bookingcom_additional_checkouts.json"
    if f2.exists():
        data = json.loads(f2.read_text(encoding="utf-8"))
        for idx, entry in enumerate(data):
            audit.append({
                "source_file": "results/bookingcom_additional_checkouts.json",
                "entry_index": idx,
                "hotel_name": entry.get("hotel_name"),
                "check_in": "2026-11-20",
                "status": "FLAGGED_PREDATES_FIX",
                "payable": entry.get("price_final_payable"),
                "fallback_risk": "Medium (Oberoi Rs 30,000 omitted taxes due to lang=hi regex mismatch)",
                "reproduced_post_fix": None,
            })

    # 3. site2_recon_results.json
    f3 = results_dir / "site2_recon_results.json"
    if f3.exists():
        data = json.loads(f3.read_text(encoding="utf-8"))
        for idx, entry in enumerate(data.get("runs", [])):
            if entry.get("slug") == "bookingcom":
                audit.append({
                    "source_file": "results/site2_recon_results.json",
                    "entry_index": idx,
                    "hotel_name": "Booking.com Recon Search",
                    "check_in": "2026-11-20",
                    "status": "FLAGGED_PREDATES_FIX",
                    "payable": entry.get("sample_price"),
                    "fallback_risk": "Catalog-only extraction (not payment review)",
                    "reproduced_post_fix": None,
                })

    out_file = Path("results/booking_payables_audit_pre_fix.json")
    out_file.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Audited {len(audit)} historical Booking.com payables. Saved to {out_file}")

if __name__ == "__main__":
    audit_booking_payables()
