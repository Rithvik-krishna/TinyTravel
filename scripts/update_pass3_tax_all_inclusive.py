import json
from pathlib import Path

pass3_file = Path("results/pass3_checkout_5hotels.json")
data = json.loads(pass3_file.read_text(encoding="utf-8"))

# Updates for Booking.com all-inclusive taxes
tax_updates = {
    ("bloomrooms city centre", "2026-11-20"): {
        "price_final_payable": 5859.0,
        "fee_lines": [
            {"label": "Room rate", "amount": 5580.0, "fee_kind": "other"},
            {"label": "Taxes & charges", "amount": 279.0, "fee_kind": "tax"}
        ],
        "spread_inr": 122.0,
        "spread_pct": 2.04,
        "screenshot": "results/recon/real_pairs/bookingcom_bloomrooms_city_centre_2026-11-20_1794892782.png"
    },
    ("ibis bengaluru city centre", "2026-11-20"): {
        "price_final_payable": 6823.95,
        "fee_lines": [
            {"label": "Room rate", "amount": 6499.0, "fee_kind": "other"},
            {"label": "Taxes & charges", "amount": 324.95, "fee_kind": "tax"}
        ],
        "spread_inr": 0.05,
        "spread_pct": 0.00,
        "screenshot": "results/recon/real_pairs/bookingcom_ibis_bengaluru_city_centre_2026-11-20_1794892805.png"
    },
    ("radisson blu atria bengaluru", "2026-11-20"): {
        "price_final_payable": 10458.0,
        "fee_lines": [
            {"label": "Room rate", "amount": 9000.0, "fee_kind": "other"},
            {"label": "Taxes & charges", "amount": 1458.0, "fee_kind": "tax"}
        ],
        "spread_inr": 619.0,
        "spread_pct": 5.59,
        "screenshot": "results/recon/real_pairs/bookingcom_radisson_blu_atria_bengaluru_2026-11-20_1794893051.png"
    },
    ("the oberoi bengaluru", "2026-11-20"): {
        "price_final_payable": 31860.0,
        "fee_lines": [
            {"label": "Room rate", "amount": 27000.0, "fee_kind": "other"},
            {"label": "Taxes & charges", "amount": 4860.0, "fee_kind": "tax"}
        ],
        "spread_inr": 60.0,
        "spread_pct": 0.19,
        "screenshot": "results/recon/real_pairs/bookingcom_the_oberoi_bengaluru_2026-11-20_1794892980.png"
    },
    ("treebo tiba", "2026-11-20"): {
        "price_final_payable": 3595.19,
        "fee_lines": [
            {"label": "Room rate", "amount": 3209.99, "fee_kind": "other"},
            {"label": "Taxes & charges", "amount": 385.20, "fee_kind": "tax"}
        ],
        "screenshot": "results/recon/real_pairs/bookingcom_treebo_tiba_2026-11-20_1794754462.png"
    }
}

for item in data:
    hotel = item.get("hotel_name", "").lower()
    cin = item.get("check_in", "")
    k = (hotel, cin)
    if k in tax_updates:
        up = tax_updates[k]
        b = item["bookingcom"]
        b["price_final_payable"] = up["price_final_payable"]
        b["fee_lines"] = up["fee_lines"]
        b["screenshot"] = up["screenshot"]
        if "spread_inr" in up and item.get("comparable"):
            item["spread_inr"] = up["spread_inr"]
            item["spread_pct"] = up["spread_pct"]

pass3_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("Updated results/pass3_checkout_5hotels.json successfully!")
