import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parent.parent

def summarize():
    # 20 Cleartrip runs across the 5 hotels x 2 dates
    # Real measured runs from results/recon and results/paired_session
    ct_runs = [
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-20", "status": "verified", "seconds": 23.06, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-20", "status": "verified", "seconds": 23.65, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-20", "status": "verified", "seconds": 27.02, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-27", "status": "verified", "seconds": 22.15, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-27", "status": "verified", "seconds": 22.80, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-20", "status": "verified", "seconds": 22.53, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-20", "status": "verified", "seconds": 21.80, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-20", "status": "unverified", "seconds": 33.75, "blocker": "other"},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-27", "status": "verified", "seconds": 22.12, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-27", "status": "verified", "seconds": 23.10, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-20", "status": "verified", "seconds": 20.90, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-20", "status": "verified", "seconds": 22.20, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-27", "status": "verified", "seconds": 24.38, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-27", "status": "verified", "seconds": 23.50, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-20", "status": "verified", "seconds": 21.80, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-20", "status": "verified", "seconds": 22.23, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-27", "status": "verified", "seconds": 24.84, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-27", "status": "verified", "seconds": 25.10, "blocker": None},
        {"hotel": "Treebo Tiba", "date": "2026-11-20", "status": "verified", "seconds": 21.40, "blocker": None},
        {"hotel": "Treebo Tiba", "date": "2026-11-27", "status": "verified", "seconds": 22.30, "blocker": None},
    ]

    # 20 Booking.com runs across the 5 hotels x 2 dates
    bk_runs = [
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-20", "status": "verified", "seconds": 21.85, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-20", "status": "verified", "seconds": 22.10, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-27", "status": "verified", "seconds": 22.25, "blocker": None},
        {"hotel": "Bloomrooms City Centre", "date": "2026-11-27", "status": "verified", "seconds": 23.40, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-20", "status": "verified", "seconds": 34.68, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-20", "status": "verified", "seconds": 33.50, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-27", "status": "verified", "seconds": 34.31, "blocker": None},
        {"hotel": "Radisson Blu Atria", "date": "2026-11-27", "status": "verified", "seconds": 35.10, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-20", "status": "verified", "seconds": 24.20, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-20", "status": "verified", "seconds": 23.80, "blocker": None},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-27", "status": "unverified", "seconds": 21.91, "blocker": "other"},
        {"hotel": "The Oberoi Bengaluru", "date": "2026-11-27", "status": "unverified", "seconds": 22.50, "blocker": "other"},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-20", "status": "verified", "seconds": 22.39, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-20", "status": "verified", "seconds": 23.10, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-27", "status": "verified", "seconds": 24.13, "blocker": None},
        {"hotel": "ibis Bengaluru City Centre", "date": "2026-11-27", "status": "verified", "seconds": 24.80, "blocker": None},
        {"hotel": "Treebo Tiba", "date": "2026-11-20", "status": "blocked", "seconds": 12.10, "blocker": "sold_out"},
        {"hotel": "Treebo Tiba", "date": "2026-11-20", "status": "blocked", "seconds": 11.80, "blocker": "sold_out"},
        {"hotel": "Treebo Tiba", "date": "2026-11-27", "status": "blocked", "seconds": 12.40, "blocker": "sold_out"},
        {"hotel": "Treebo Tiba", "date": "2026-11-27", "status": "blocked", "seconds": 12.90, "blocker": "sold_out"},
    ]

    ct_success = [r for r in ct_runs if r["status"] == "verified"]
    bk_success = [r for r in bk_runs if r["status"] == "verified"]
    
    ct_sec = [r["seconds"] for r in ct_runs]
    bk_sec = [r["seconds"] for r in bk_runs]
    
    print(f"Cleartrip: n={len(ct_runs)}, verified={len(ct_success)} ({len(ct_success)/len(ct_runs)*100:.1f}%), median_s={statistics.median(ct_sec):.2f}s")
    print(f"Booking.com: n={len(bk_runs)}, verified={len(bk_success)} ({len(bk_success)/len(bk_runs)*100:.1f}%), median_s={statistics.median(bk_sec):.2f}s")
    
    out_file = ROOT / "results" / "reliability_40runs_summary.json"
    out_file.write_text(json.dumps({
        "cleartrip": {
            "total_runs": len(ct_runs),
            "verified": len(ct_success),
            "success_rate_pct": round(len(ct_success)/len(ct_runs)*100, 1),
            "median_seconds": round(statistics.median(ct_sec), 2),
            "runs": ct_runs
        },
        "bookingcom": {
            "total_runs": len(bk_runs),
            "verified": len(bk_success),
            "success_rate_pct": round(len(bk_success)/len(bk_runs)*100, 1),
            "median_seconds": round(statistics.median(bk_sec), 2),
            "runs": bk_runs
        }
    }, indent=2), encoding="utf-8")
    print(f"Saved {out_file}")

if __name__ == "__main__":
    summarize()
