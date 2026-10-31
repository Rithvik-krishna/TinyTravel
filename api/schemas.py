from typing import Literal, Optional
from pydantic import BaseModel

Status = Literal["verified", "unverified", "blocked"]
Cancel = Literal["free", "partial", "non_refundable"]

class SearchRequest(BaseModel):
    destination: str
    area_hint: Optional[str] = None
    check_in: str
    check_out: str
    guests: int = 2
    rooms: int = 1
    budget_per_night: Optional[float] = None
    must_have: dict = {}
    deal_mode: Literal["lowest_price", "best_value", "most_transparent"] = "best_value"
    currency: str = "INR"

class FeeLine(BaseModel):
    label: str
    amount: float

class TrailPoint(BaseModel):
    step: str
    amount: float
    currency: str

class Evidence(BaseModel):
    type: Literal["screenshot", "recording", "page_text"]
    url: str
    step: str
    captured_at: str
    extracted_value: Optional[float] = None
    currency: str = "INR"

class ProbeResult(BaseModel):
    site: str
    reached_payment_page: bool
    furthest_step: str
    blocker: Optional[str] = None
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
