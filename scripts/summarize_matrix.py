import json

data = json.load(open('results/3demo_hotels_matrix_results.json'))
print(f"Total runs: {len(data)}")
for r in data:
    hotel = r['hotel']
    date = r['check_in']
    run_idx = r['run_index']
    ct_p = r['cleartrip']['payable']
    bk_p = r['bookingcom']['payable']
    comp = r['comparison']['status']
    spread = r['comparison']['spread_inr']
    pct = r['comparison']['spread_pct']
    reason = r['comparison']['reason']
    ct_sec = r['cleartrip']['seconds']
    bk_sec = r['bookingcom']['seconds']
    ct_p_str = f"₹{ct_p:>7.1f}" if ct_p is not None else "   None"
    bk_p_str = f"₹{bk_p:>7.1f}" if bk_p is not None else "   None"
    spread_str = f"{spread:>6.1f}" if spread is not None else "  None"
    pct_str = f"{pct:>4.1f}%" if pct is not None else "None%"
    print(f"{hotel:28} | {date} | #{run_idx} | CT: {ct_p_str} ({ct_sec:>4.1f}s) | BK: {bk_p_str} ({bk_sec:>4.1f}s) | {comp:14} | Spread: {spread_str} ({pct_str}) | {reason}")
