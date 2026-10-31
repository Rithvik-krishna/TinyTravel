import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.scoring import fee_leak_pct, reconciles, verified
from services.dedupe import name_confidence, match_status

demo = json.loads((Path(__file__).parents[2] / "fixtures/demo_run.json").read_text())

def test_fee_leak_matches_fixture():
    for o in demo["offers"]:
        assert fee_leak_pct(o["price_shown_on_listing"], o["price_final_payable"]) == o["fee_leak_pct"]

def test_verified_offers_reconcile_and_have_evidence():
    for o in demo["offers"]:
        assert bool(verified(o)) == (o["status"] == "verified"), o["offer_id"]

def test_real_cleartrip_numbers():
    o = next(x for x in demo["offers"] if x["offer_id"] == "h1_cleartrip")
    assert o["price_final_payable"] == 11276 and o["fee_leak_pct"] == 37.3
    assert reconciles(o["fee_lines"], 11276)

def test_dedupe_thresholds():
    assert match_status(name_confidence("La Marvella", "La Marvella")) == "merged"
    assert match_status(name_confidence("Urban Nest Inn", "Urban Nest Inn & Suites")) in ("suggested", "merged")
