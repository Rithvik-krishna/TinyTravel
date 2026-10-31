"""Executable API Models for TinyTravel.
Mirrors fixtures/demo_run.json exactly (Pydantic v2, extra="forbid").
"""
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Status = Literal["verified", "unverified", "blocked"]
CancelCategory = Literal["free", "partial", "non_refundable"]
Reconciliation = Literal["ok", "mismatch"]
Blocker = Literal["captcha", "login", "otp", "timeout", "other"]
DealMode = Literal["lowest_price", "best_value", "most_transparent"]
MatchStatus = Literal["merged", "suggested"]
TravellerType = Literal["solo", "couple", "friends", "family", "business"]
EvidenceType = Literal["screenshot", "recording", "page_text"]


class BaseModelForbid(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class MetaInfo(BaseModelForbid):
    mock: bool = False
    label: Optional[str] = None
    saved_run_label: Optional[str] = None
    note: Optional[str] = None


class SearchRequestOut(BaseModelForbid):
    destination: str
    area_hint: Optional[str] = None
    check_in: str
    check_out: str
    guests: int = 2
    rooms: int = 1
    budget_per_night: Optional[float] = None
    must_have: dict[str, bool] = {}
    deal_mode: DealMode = "best_value"
    currency: str = "INR"
    mock: bool = False
    raw_text: Optional[str] = None


class SearchInput(BaseModelForbid):
    """Accepted payload for POST /api/search."""
    text: Optional[str] = None
    destination: Optional[str] = None
    area_hint: Optional[str] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    guests: int = 2
    rooms: int = 1
    budget_per_night: Optional[float] = None
    must_have: dict[str, bool] = {}
    deal_mode: DealMode = "best_value"
    currency: str = "INR"
    raw_text: Optional[str] = None
    mock: bool = False
    # Target mode (skips discovery during live demo segment)
    hotel_name: Optional[str] = None
    platforms: Optional[list[str]] = None


class SearchResponse(BaseModelForbid):
    search_id: str


class TravelProfile(BaseModelForbid):
    traveller_type: TravellerType
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    hotel_type: str = "any"
    min_rating: Optional[float] = None
    must_have: list[str] = []
    prefers_refundable: bool = True
    deal_mode: DealMode = "best_value"


class Hotel(BaseModelForbid):
    hotel_id: str
    canonical_name: str
    area: str
    rating: Optional[float] = None


class Listing(BaseModelForbid):
    listing_id: str
    platform: str
    hotel_name: str
    address: Optional[str] = None
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    shown_price: Optional[float] = None
    currency: str = "INR"
    source_url: str
    captured_at: str
    mock: bool = False


class HotelGroup(BaseModelForbid):
    hotel_id: str
    canonical_name: str
    area: str
    match_status: MatchStatus
    confidence: float
    why: str
    offer_ids: list[str]


class FeeLine(BaseModelForbid):
    label: str
    amount: float


class TrailPoint(BaseModelForbid):
    step: str
    amount: float
    currency: str = "INR"


class Evidence(BaseModelForbid):
    type: EvidenceType
    url: str
    step: str
    captured_at: str
    extracted_value: Optional[float] = None
    currency: str = "INR"
    mock: bool = False


class TransparencyBreakdown(BaseModelForbid):
    fee_leak: Optional[float] = None
    addons_pressure: Optional[float] = None
    price_stability: Optional[float] = None
    evidence: Optional[float] = None


class Transparency(BaseModelForbid):
    score: Optional[float] = None
    breakdown: Optional[TransparencyBreakdown] = None
    note: str


class ProbeResult(BaseModelForbid):
    site: str = ""
    reached_payment_page: bool = False
    furthest_step: str = "unknown"
    blocker: Optional[Blocker] = None
    hotel_name: str = ""
    hotel_url: str = ""
    room_type: str = ""
    max_occupancy: Optional[int] = None
    meal_plan: str = ""
    cancellation_policy: str = ""
    price_shown_on_listing: Optional[float] = None
    price_shown_on_room_selection: Optional[float] = None
    price_final_payable: Optional[float] = None
    fee_lines: list[FeeLine] = []
    preselected_addons: list[str] = []
    urgency_or_scarcity_messages: list[str] = []
    price_trail: list[TrailPoint] = []
    currency: str = "INR"
    notes: str = ""
    listing_page_text: Optional[str] = None
    payment_page_text: Optional[str] = None


class Offer(BaseModelForbid):
    offer_id: str
    hotel_id: str
    run_id: str
    streaming_url: Optional[str] = None
    started_at: str
    finished_at: str
    steps: int
    cost_usd: float
    status: Status
    reconciliation: Optional[Reconciliation] = None
    cancellation_category: Optional[CancelCategory] = None
    site: str
    reached_payment_page: bool
    furthest_step: str
    blocker: Optional[Blocker] = None
    hotel_name: str
    hotel_url: str
    room_type: str = ""
    max_occupancy: Optional[int] = None
    meal_plan: str = ""
    cancellation_policy: str = ""
    price_shown_on_listing: Optional[float] = None
    price_shown_on_room_selection: Optional[float] = None
    price_final_payable: Optional[float] = None
    fee_lines: list[FeeLine] = []
    preselected_addons: list[str] = []
    urgency_or_scarcity_messages: list[str] = []
    price_trail: list[TrailPoint] = []
    currency: str = "INR"
    notes: str = ""
    fee_leak_pct: Optional[float] = None
    evidence: list[Evidence] = []
    mock: bool = False
    transparency: Optional[Transparency] = None
    listing_page_text: Optional[str] = None
    payment_page_text: Optional[str] = None


class RankingItem(BaseModelForbid):
    offer_id: str
    total: float
    components: dict[str, float]
    weights: dict[str, float]


class VerdictPick(BaseModelForbid):
    cheapest_verified: Optional[str] = None
    safe_cheapest: Optional[str] = None
    best_for_you: Optional[str] = None
    headlines: dict[str, str] = {}


class NonComparableWarning(BaseModelForbid):
    hotel_id: str
    offer_id: str
    message: str


class Verdicts(BaseModelForbid):
    deal_mode: DealMode
    hero_hotel_id: str
    ranking: list[RankingItem] = []
    overall: VerdictPick
    per_hotel: dict[str, VerdictPick] = {}
    non_comparable_warnings: list[NonComparableWarning] = []
    mock: bool = False


class SelectionCard(BaseModelForbid):
    hotel: str
    room_type: str
    meal_plan: str
    cancellation: str
    dates: str
    guests: int = 2
    expected_final_payable: Optional[float] = None
    currency: str = "INR"
    verified_at: str


class CopyPastePack(BaseModelForbid):
    name: str
    email: str
    phone: str


class HandoffPack(BaseModelForbid):
    offer_id: str
    platform: str
    deep_link: str
    qr_png_base64: str = ""
    qr_note: Optional[str] = None
    selection_card: SelectionCard
    copy_paste: CopyPastePack
    disclaimer: str
    mock: bool = False


class RecheckSnapshot(BaseModelForbid):
    amount: float
    at: str


class TrailDiffItem(BaseModelForbid):
    step: str
    before: float
    after: float


class Recheck(BaseModelForbid):
    recheck_id: str
    offer_id: str
    status: str
    previous: RecheckSnapshot
    current: RecheckSnapshot
    delta: float
    delta_pct: float
    elapsed_minutes: int
    trail_diff: list[TrailDiffItem] = []
    message: str
    mock: bool = False


class SummaryStrip(BaseModelForbid):
    listings_found: int
    unique_hotels: int
    verified: int
    unverified: int
    blocked: int
    avg_fee_leak_pct: Optional[float] = None


class ResultsResponse(BaseModelForbid):
    meta: MetaInfo = Field(..., alias="_meta")
    search_request: SearchRequestOut
    travel_profile: TravelProfile
    hotels: list[Hotel]
    listings: list[Listing]
    hotel_groups: list[HotelGroup]
    offers: list[Offer]
    verdicts: Verdicts
    handoff: HandoffPack
    rechecks: list[Recheck]
    summary_strip: SummaryStrip
