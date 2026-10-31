"""Fee classification and glossary service for TinyTravel.
Provides static definitions for fee kinds and classifies raw fee line labels.
"""
from typing import Literal

FeeKind = Literal["tax", "platform_fee", "property_fee", "add_on", "other"]

FEE_GLOSSARY: dict[str, dict] = {
    "gst_taxes": {
        "kind": "tax",
        "name": "Goods & Services Tax (GST) / Taxes",
        "description": "Statutory charges and government levies (such as GST or municipal luxury taxes) imposed by public authorities. Typically calculated as a percentage of the room tariff.",
        "examples": ["Hotel taxes", "GST", "Taxes & fees", "Taxes & charges", "Taxes & service fees"],
    },
    "convenience_fee": {
        "kind": "platform_fee",
        "name": "Convenience Fee",
        "description": "A fee charged by booking platforms to facilitate online transactions, payment processing, and digital infrastructure maintenance.",
        "examples": ["Convenience fee", "Booking fee", "Online facilitation fee"],
    },
    "platform_service_fee": {
        "kind": "platform_fee",
        "name": "Platform Service Fee",
        "description": "An administrative charge that may typically be applied by online booking intermediaries for reservation handling, platform support, and customer care.",
        "examples": ["Platform fee", "Service fee", "Processing fee"],
    },
    "payment_gateway_fee": {
        "kind": "platform_fee",
        "name": "Payment Gateway Fee",
        "description": "A payment processing surcharge that may be applied depending on the chosen payment method (e.g. credit card processing or net banking).",
        "examples": ["Payment gateway fee", "Payment processing fee"],
    },
    "resort_property_fee": {
        "kind": "property_fee",
        "name": "Resort / Facility Fee",
        "description": "A charge that may be levied by certain properties or resorts for on-site amenities (such as pool access, fitness center, Wi-Fi, or grounds maintenance).",
        "examples": ["Resort fee", "Facility fee", "Amenity fee", "Destination fee"],
    },
    "trip_protection_addon": {
        "kind": "add_on",
        "name": "Trip Protection & Add-ons",
        "description": "Optional ancillary products such as travel insurance, flexible cancellation passes, or carbon offset contributions that may be pre-selected during checkout.",
        "examples": ["Trip protection", "Travel insurance", "Flex cancellation pass", "Baggage protection"],
    },
    "base_room_rate": {
        "kind": "other",
        "name": "Base Room Tariff",
        "description": "The base room tariff for the selected room type and duration of stay before statutory taxes and platform fees.",
        "examples": ["Room price", "Room price (base)", "1 room x 1 night"],
    },
    "discount_promo": {
        "kind": "other",
        "name": "Discounts & Promo Deductions",
        "description": "Promotional rate reductions, platform discounts, or coupon code deductions that may typically be applied to reduce total payable amount.",
        "examples": ["Discount", "Offer / coupon", "Coupon discount", "Property discount"],
    },
}


def classify_fee_label(label: str) -> FeeKind:
    """Classify a fee line label into a standardized FeeKind.
    Returns: 'tax' | 'platform_fee' | 'property_fee' | 'add_on' | 'other'
    """
    if not label:
        return "other"
    l = label.lower().strip()

    # 1. Taxes: GST, VAT, taxes, levies
    if any(k in l for k in ["tax", "gst", "vat", "levy", "statutory", "government"]):
        return "tax"
    if "charges" in l and any(k in l for k in ["tax", "fee"]):
        return "tax"

    # 2. Add-ons: insurance, protection, flex, donation, assistance, carbon
    if any(k in l for k in ["insurance", "protect", "flex", "donation", "addon", "add-on", "assistance", "carbon"]):
        return "add_on"

    # 3. Property fees: resort, facility, amenity, cleaning, destination
    if any(k in l for k in ["resort", "facility", "amenity", "cleaning", "destination"]):
        return "property_fee"

    # 4. Platform fees: convenience, booking, processing, payment gateway, gateway, platform
    if any(k in l for k in ["convenience", "gateway", "booking fee", "processing fee", "platform"]):
        return "platform_fee"
    if "service fee" in l and "tax" not in l:
        return "platform_fee"

    # 5. Base rates, discounts, coupons, others
    return "other"
