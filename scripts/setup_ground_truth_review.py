import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def setup():
    old_p = ROOT / "results" / "ground_truth_payment_pages.csv"
    renamed_p = ROOT / "results" / "ground_truth_auto_generated_not_human_verified.csv"
    
    if old_p.exists():
        if renamed_p.exists():
            renamed_p.unlink()
        old_p.rename(renamed_p)
        print(f"Renamed {old_p.name} -> {renamed_p.name}")
        
    # Read the 30 rows from the renamed file to create the blank review sheet
    rows = []
    if renamed_p.exists():
        with open(renamed_p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)
                
    review_p = ROOT / "results" / "ground_truth_review_sheet.csv"
    with open(review_p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "row_id", "platform", "hotel_name", "check_in_date",
            "screenshot_path", "parsed_payable", "human_value", "notes"
        ])
        for r in rows[:30]:
            writer.writerow([
                r.get("row_id"),
                r.get("platform"),
                r.get("hotel_name"),
                r.get("check_in_date"),
                r.get("screenshot_path"),
                r.get("parsed_payable"),
                "",  # empty human_value column
                r.get("notes", "")
            ])
            
    print(f"Created blank review sheet: {review_p} (30 rows, human_value empty)")

def compute_accuracy(csv_path: Path):
    if not csv_path.exists():
        return "NOT MEASURED"
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        filled = 0
        matches = 0
        for r in reader:
            hv = r.get("human_value", "").strip()
            if hv:
                filled += 1
                try:
                    h_val = float(hv)
                    p_val = float(r.get("parsed_payable", 0))
                    if abs(h_val - p_val) <= 0.01:
                        matches += 1
                except ValueError:
                    pass
        if filled == 0:
            return "NOT MEASURED"
        return f"{(matches / filled) * 100:.1f}% ({matches}/{filled} filled rows)"

if __name__ == "__main__":
    setup()
    acc = compute_accuracy(ROOT / "results" / "ground_truth_review_sheet.csv")
    print(f"Current Accuracy: {acc}")
