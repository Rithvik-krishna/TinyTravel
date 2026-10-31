"""Pure functions. Golden-tested against fixtures/demo_run.json."""
def fee_leak_pct(listing, final):
    if not listing or final is None: return None
    return round((final - listing) / listing * 100, 1)

def reconciles(fee_lines, final, tol=0.01):
    if final is None or not fee_lines: return False
    return abs(sum(l["amount"] for l in fee_lines) - final) <= tol * final

def verified(o):
    return (o.get("reached_payment_page") and o.get("price_final_payable") is not None
            and len(o.get("evidence", [])) > 0 and reconciles(o.get("fee_lines", []), o["price_final_payable"]))

# TODO (M2): transparency_score, rank_offers, pick_verdicts (assumptions in TinyTravel_Phased_Plan.md section 4)
