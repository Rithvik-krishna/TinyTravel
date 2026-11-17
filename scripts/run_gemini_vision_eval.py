import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REAL_PAIRS = ROOT / "results" / "recon" / "real_pairs"

SAMPLE_10_SCREENSHOTS = [
    "cleartrip_bloomrooms_city_centre_2026-11-20_1794895211.png",
    "bookingcom_bloomrooms_city_centre_2026-11-20_1794895236.png",
    "cleartrip_bloomrooms_city_centre_2026-11-27_1794895260.png",
    "bookingcom_bloomrooms_city_centre_2026-11-27_1794895284.png",
    "cleartrip_radisson_blu_atria_bengaluru_2026-11-20_1794895308.png",
    "bookingcom_radisson_blu_atria_bengaluru_2026-11-20_1794895333.png",
    "cleartrip_radisson_blu_atria_bengaluru_2026-11-27_1794895370.png",
    "bookingcom_radisson_blu_atria_bengaluru_2026-11-27_1794895394.png",
    "cleartrip_the_oberoi_bengaluru_2026-11-20_1794895957.png",
    "bookingcom_the_oberoi_bengaluru_2026-11-20_1794895532.png",
]

async def evaluate():
    from api.services.dual_extraction import extract_via_gemini_vision, parse_dom_payment_text
    
    api_key = os.getenv("GEMINI_API_KEY")
    results = []
    
    for shot_name in SAMPLE_10_SCREENSHOTS:
        shot_path = REAL_PAIRS / shot_name
        txt_path = shot_path.with_suffix(".txt")
        
        dom_val = None
        if txt_path.exists():
            dom_parsed = parse_dom_payment_text(txt_path.read_text(encoding="utf-8"))
            dom_val = dom_parsed.get("total_payable")
            
        if not api_key:
            results.append({
                "screenshot": str(shot_path.relative_to(ROOT)).replace("\\", "/"),
                "dom_payable": dom_val,
                "vision_payable": "NOT RUN",
                "status": "NOT RUN (GEMINI_API_KEY unset)",
                "diff_pct": "NOT RUN"
            })
        else:
            vis_res = await extract_via_gemini_vision(shot_path)
            if vis_res:
                v_p = vis_res.get("total_payable")
                diff = round(abs(dom_val - v_p) / dom_val * 100, 2) if dom_val and v_p else None
                results.append({
                    "screenshot": str(shot_path.relative_to(ROOT)).replace("\\", "/"),
                    "dom_payable": dom_val,
                    "vision_payable": v_p,
                    "status": "MATCH" if diff and diff <= 1.0 else "MISMATCH",
                    "diff_pct": f"{diff}%" if diff is not None else "N/A"
                })
            else:
                results.append({
                    "screenshot": str(shot_path.relative_to(ROOT)).replace("\\", "/"),
                    "dom_payable": dom_val,
                    "vision_payable": "ERROR",
                    "status": "ERROR",
                    "diff_pct": "N/A"
                })
                
    out_file = ROOT / "results" / "gemini_vision_eval_10shots.json"
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Vision evaluation output saved to {out_file}")

if __name__ == "__main__":
    asyncio.run(evaluate())
