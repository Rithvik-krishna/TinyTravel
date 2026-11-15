import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
import shutil

from api.agents.playbooks.cleartrip import run_cleartrip_playbook
from api.agents.playbooks.bookingcom import run_bookingcom_playbook
from api.services.normalize import normalize_room_tier, normalize_meal_plan, are_offers_comparable

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tinytravel.real_pairs")
IST = timezone(timedelta(hours=5, minutes=30))

HOTELS = [
    "Radisson Blu Atria Bengaluru",
    "Sterlings Mac Hotel",
    "La Marvella",
    "The Chancery Pavilion",
    "The Pride Hotel",
    "Bloomrooms City Centre",
    "Treebo Tiba",
    "ibis Bengaluru City Centre",
]

DATES = [
    {"label": "Nov 20-21", "cin": "2026-11-20", "cout": "2026-11-21"},
    {"label": "Nov 27-28", "cin": "2026-11-27", "cout": "2026-11-28"},
]


async def run_all_pairs():
    recon_dir = Path("results/recon/real_pairs")
    recon_dir.mkdir(parents=True, exist_ok=True)

    all_runs = []
    total_runs = len(HOTELS) * len(DATES) * 2  # 8 * 2 * 2 = 32
    run_idx = 0

    for d in DATES:
        cin = d["cin"]
        cout = d["cout"]
        d_lbl = d["label"]
        params = {"check_in": cin, "check_out": cout, "guests": 2}

        # 1. Cleartrip runs (Headless)
        for h in HOTELS:
            run_idx += 1
            logger.info(">>> [%d/%d] Cleartrip: '%s' on %s", run_idx, total_runs, h, d_lbl)
            t0 = datetime.now(IST)
            slug = h.lower().replace(" ", "_").replace("@", "").replace("-", "_")
            scr_target = recon_dir / f"cleartrip_{slug}_{cin}.png"
            
            try:
                res = await run_cleartrip_playbook(h, params, headless=True)
                dur = (datetime.now(IST) - t0).total_seconds()
                
                # Check for evidence screenshot in evidence/cleartrip
                ev_dir = Path("evidence/cleartrip")
                ev_scrs = list(ev_dir.glob("cleartrip_payment_*.png"))
                if ev_scrs:
                    ev_scrs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    latest_ev = ev_scrs[0]
                    shutil.copyfile(latest_ev, scr_target)
                    res["screenshot_path"] = str(scr_target)
                elif scr_target.exists():
                    res["screenshot_path"] = str(scr_target)
                else:
                    res["screenshot_path"] = None

                res["date_label"] = d_lbl
                res["check_in"] = cin
                res["check_out"] = cout
                res["duration_seconds"] = round(dur, 2)
                all_runs.append(res)
                logger.info("<<< Cleartrip done in %.2fs: reached_payment=%s payable=%s room=%s meal=%s cancel=%s",
                            dur, res.get("reached_payment_page"), res.get("price_final_payable"),
                            res.get("room_type"), res.get("meal_plan"), res.get("cancellation_policy"))
            except Exception as e:
                logger.error("Cleartrip run failed: %s", e)
                all_runs.append({
                    "site": "Cleartrip", "hotel_name": h, "check_in": cin, "check_out": cout,
                    "date_label": d_lbl, "reached_payment_page": False, "blocker": "other",
                    "price_final_payable": None, "notes": str(e), "fee_lines": []
                })
            await asyncio.sleep(2.0)

        # 2. Booking.com runs (Headed)
        for h in HOTELS:
            run_idx += 1
            logger.info(">>> [%d/%d] Booking.com: '%s' on %s", run_idx, total_runs, h, d_lbl)
            t0 = datetime.now(IST)
            slug = h.lower().replace(" ", "_").replace("@", "").replace("-", "_")
            scr_target = recon_dir / f"bookingcom_{slug}_{cin}.png"

            try:
                res = await run_bookingcom_playbook(h, params, headless=False)
                dur = (datetime.now(IST) - t0).total_seconds()

                if scr_target.exists():
                    res["screenshot_path"] = str(scr_target)
                else:
                    res["screenshot_path"] = None

                res["date_label"] = d_lbl
                res["check_in"] = cin
                res["check_out"] = cout
                res["duration_seconds"] = round(dur, 2)
                all_runs.append(res)
                logger.info("<<< Booking.com done in %.2fs: reached_payment=%s payable=%s room=%s meal=%s cancel=%s",
                            dur, res.get("reached_payment_page"), res.get("price_final_payable"),
                            res.get("room_type"), res.get("meal_plan"), res.get("cancellation_policy"))
            except Exception as e:
                logger.error("Booking.com run failed: %s", e)
                all_runs.append({
                    "site": "Booking.com", "hotel_name": h, "check_in": cin, "check_out": cout,
                    "date_label": d_lbl, "reached_payment_page": False, "blocker": "other",
                    "price_final_payable": None, "notes": str(e), "fee_lines": []
                })
            await asyncio.sleep(3.0)

    # Save raw 32 runs
    with open("results/real_pairs_32runs.json", "w", encoding="utf-8") as f:
        json.dump(all_runs, f, indent=2)
    logger.info("Saved 32 runs to results/real_pairs_32runs.json")

    # Run cohort comparison
    comparisons = []
    for d in DATES:
        cin = d["cin"]
        d_lbl = d["label"]
        for h in HOTELS:
            ct = next((r for r in all_runs if r["site"] == "Cleartrip" and r["hotel_name"] == h and r["check_in"] == cin), None)
            bk = next((r for r in all_runs if r["site"] == "Booking.com" and r["hotel_name"] == h and r["check_in"] == cin), None)

            p_ct = ct.get("price_final_payable") if ct else None
            p_bk = bk.get("price_final_payable") if bk else None

            # Check verified status
            ct_ver = ct.get("reached_payment_page") and p_ct is not None
            bk_ver = bk.get("reached_payment_page") and p_bk is not None

            if not ct_ver or not bk_ver:
                comparisons.append({
                    "hotel_name": h,
                    "date": d_lbl,
                    "cleartrip_payable": p_ct,
                    "bookingcom_payable": p_bk,
                    "status": "UNMEASURED_OR_BLOCKED",
                    "comparable": False,
                    "reason": f"Cleartrip ver={ct_ver}, Booking.com ver={bk_ver}",
                    "spread_inr": None,
                    "spread_pct": None,
                    "cleartrip_cohort": {
                        "room": ct.get("room_type") if ct else None,
                        "meal": ct.get("meal_plan") if ct else None,
                        "cancel": ct.get("cancellation_policy") if ct else None,
                    },
                    "bookingcom_cohort": {
                        "room": bk.get("room_type") if bk else None,
                        "meal": bk.get("meal_plan") if bk else None,
                        "cancel": bk.get("cancellation_policy") if bk else None,
                    }
                })
                continue

            # Compare the 4 dimensions
            ct_room_tier = normalize_room_tier(ct.get("room_type", "Standard"))
            bk_room_tier = normalize_room_tier(bk.get("room_type", "Standard"))
            ct_meal = normalize_meal_plan(ct.get("meal_plan", "Room Only"))
            bk_meal = normalize_meal_plan(bk.get("meal_plan", "Room Only"))
            ct_cancel = "free" if "free" in ct.get("cancellation_policy", "").lower() else "non_refundable"
            bk_cancel = "free" if "free" in bk.get("cancellation_policy", "").lower() else "non_refundable"
            ct_occ = ct.get("max_occupancy", 2)
            bk_occ = bk.get("max_occupancy", 2)

            mismatches = []
            if ct_room_tier != bk_room_tier:
                mismatches.append(f"room tier ({ct_room_tier} vs {bk_room_tier})")
            if ct_occ != bk_occ:
                mismatches.append(f"occupancy ({ct_occ} vs {bk_occ})")
            if ct_meal != bk_meal:
                mismatches.append(f"meal ({ct_meal} vs {bk_meal})")
            if ct_cancel != bk_cancel:
                mismatches.append(f"cancellation ({ct_cancel} vs {bk_cancel})")

            if mismatches:
                comparisons.append({
                    "hotel_name": h,
                    "date": d_lbl,
                    "cleartrip_payable": p_ct,
                    "bookingcom_payable": p_bk,
                    "status": "NOT COMPARABLE",
                    "comparable": False,
                    "reason": "Mismatch in " + ", ".join(mismatches),
                    "spread_inr": None,
                    "spread_pct": None,
                    "cleartrip_cohort": {
                        "room": ct.get("room_type"),
                        "tier": ct_room_tier,
                        "meal": ct_meal,
                        "cancel": ct_cancel,
                    },
                    "bookingcom_cohort": {
                        "room": bk.get("room_type"),
                        "tier": bk_room_tier,
                        "meal": bk_meal,
                        "cancel": bk_cancel,
                    }
                })
            else:
                spread_inr = round(abs(p_ct - p_bk), 2)
                min_p = min(p_ct, p_bk)
                spread_pct = round((spread_inr / min_p) * 100, 2) if min_p > 0 else 0.0
                comparisons.append({
                    "hotel_name": h,
                    "date": d_lbl,
                    "cleartrip_payable": p_ct,
                    "bookingcom_payable": p_bk,
                    "status": "COMPARABLE",
                    "comparable": True,
                    "reason": "All 4 dimensions match identically",
                    "spread_inr": spread_inr,
                    "spread_pct": spread_pct,
                    "cleartrip_cohort": {
                        "room": ct.get("room_type"),
                        "tier": ct_room_tier,
                        "meal": ct_meal,
                        "cancel": ct_cancel,
                    },
                    "bookingcom_cohort": {
                        "room": bk.get("room_type"),
                        "tier": bk_room_tier,
                        "meal": bk_meal,
                        "cancel": bk_cancel,
                    }
                })

    with open("results/real_pairs_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparisons, f, indent=2)
    logger.info("Saved comparison results to results/real_pairs_comparison.json")

    # Print summary table
    print("\n" + "=" * 95)
    print(f"{'Hotel':<30} | {'Date':<10} | {'Cleartrip (₹)':<14} | {'Booking.com (₹)':<15} | {'Status':<14} | {'Spread %':<10}")
    print("-" * 95)
    for c in comparisons:
        ct_p = f"₹{c['cleartrip_payable']:,.0f}" if c['cleartrip_payable'] else "N/A"
        bk_p = f"₹{c['bookingcom_payable']:,.0f}" if c['bookingcom_payable'] else "N/A"
        spr = f"{c['spread_pct']:.1f}%" if c['spread_pct'] is not None else "--"
        print(f"{c['hotel_name'][:29]:<30} | {c['date']:<10} | {ct_p:<14} | {bk_p:<15} | {c['status']:<14} | {spr:<10}")
    print("=" * 95)


if __name__ == "__main__":
    asyncio.run(run_all_pairs())
