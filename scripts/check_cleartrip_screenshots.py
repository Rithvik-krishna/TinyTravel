import json
import re
from pathlib import Path
from collections import defaultdict

ct_map = defaultdict(list)

for f in Path("results").glob("*.json"):
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r'([^\s"\'\\]*cleartrip[^\s"\'\\]*\.png)', txt)
        for m in set(matches):
            ct_map[m].append(f.name)
    except Exception:
        pass

print(f"Total distinct Cleartrip PNGs referenced across results/*.json: {len(ct_map)}")
shared = {k: v for k, v in ct_map.items() if len(v) > 1}
print(f"Number of Cleartrip PNGs referenced in more than one json file: {len(shared)}")

# Also check inside individual json files for internal sharing across runs
print("\n--- Checking internal sharing within files ---")
for f in Path("results").glob("*.json"):
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(data, list):
            file_shots = defaultdict(list)
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    # Check Cleartrip subdict
                    ct = item.get("cleartrip", {}) if isinstance(item.get("cleartrip"), dict) else item
                    hotel = item.get("hotel_name") or ct.get("hotel_name")
                    cin = item.get("check_in") or ct.get("check_in")
                    # search for any png string in ct dict
                    txt_ct = json.dumps(ct)
                    pngs = re.findall(r'([^\s"\'\\]*cleartrip[^\s"\'\\]*\.png)', txt_ct)
                    for p in pngs:
                        file_shots[p].append((idx, hotel, cin))
            internal_shared = {k: v for k, v in file_shots.items() if len(v) > 1}
            if internal_shared:
                print(f"File {f.name} has {len(internal_shared)} shared Cleartrip screenshots across runs:")
                for k, v in internal_shared.items():
                    print(f"  {k} shared across {len(v)} runs: {v}")
    except Exception:
        pass
