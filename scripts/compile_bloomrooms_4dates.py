import json
from pathlib import Path

# Load Date 1 & 2
with open("results/bloomrooms_current_rerun.json", encoding="utf-8") as f:
    d12 = json.load(f)

# Load Date 3 & 4
with open("results/bloomrooms_dates3_4.json", encoding="utf-8") as f:
    d34 = json.load(f)

# Ensure room_type for CT in d12 is updated to "Standard Twin Room" as verified from page text
for r in d12:
    if r["site"] == "Cleartrip" and r["room_type"] == "Room Only":
        r["room_type"] = "Standard Twin Room"
    r["occupancy"] = "1 Room, 2 Adults"

all_runs = d12 + d34
out_path = Path("results/bloomrooms_4dates_complete.json")
out_path.write_text(json.dumps(all_runs, indent=2), encoding="utf-8")
print(f"Compiled {len(all_runs)} runs into {out_path}")
