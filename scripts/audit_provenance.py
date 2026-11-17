import json
from pathlib import Path

def audit_pass3():
    p = Path('results/pass3_checkout_5hotels.json')
    if not p.exists():
        print("pass3 file not found")
        return
    data = json.loads(p.read_text(encoding='utf-8'))
    print("=== PASS 3 PROVENANCE AUDIT ===")
    for i, d in enumerate(data):
        hotel = d.get('hotel_name')
        cin = d.get('check_in')
        bk = d.get('bookingcom', {})
        p_val = bk.get('price_final_payable')
        ss = bk.get('screenshot')
        fl = bk.get('fee_lines')
        
        # Check provenance
        # Bloomrooms 2026-11-20 was explicitly printed Rs 5,859
        # ibis 2026-11-20 was explicitly printed Rs 6,823.95
        # The Oberoi 2026-11-20 was explicitly printed Rs 31,860
        # Radisson Blu Atria was 10,458 (script recomputed 9000 + 1458, page printed 9,558)
        # Treebo Tiba 3595.19 (script recomputed 3209.99 + 385.20)
        # All 2026-11-27 were pre-tax or unverified
        print(f"Row {i+1}: {hotel} [{cin}] -> Booking.com: INR {p_val}")

def audit_saved_run():
    p = Path('fixtures/saved_run.json')
    if not p.exists():
        print("saved_run.json not found")
        return
    data = json.loads(p.read_text(encoding='utf-8'))
    print("\n=== SAVED_RUN.JSON PROVENANCE AUDIT ===")
    offers = data.get('offers', [])
    for off in offers:
        site = off.get('site')
        hotel = off.get('hotel_name')
        p_val = off.get('price_final_payable')
        print(f"Offer {off.get('offer_id')}: site={site}, hotel={hotel}, payable={p_val}")

if __name__ == '__main__':
    audit_pass3()
    audit_saved_run()
