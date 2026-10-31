"""Executable SSE Event Models for TinyTravel.
Mirrors fixtures/sse_script.json exactly (Pydantic v2, extra="forbid").
"""
from typing import Literal, Optional, Union
from pydantic import BaseModel, ConfigDict

try:
    from .models import BaseModelForbid, SearchRequestOut, HotelGroup, Status
except ImportError:
    from models import BaseModelForbid, SearchRequestOut, HotelGroup, Status


class ParsedEventData(BaseModelForbid):
    search_request: SearchRequestOut


class DiscoveryStartedEventData(BaseModelForbid):
    platforms: list[str]


class ListingsFoundEventData(BaseModelForbid):
    count: int
    by_platform: dict[str, int]


class HotelsGroupedEventData(BaseModelForbid):
    hotel_groups: list[HotelGroup]


class AgentStartedEventData(BaseModelForbid):
    run_id: str
    offer_id: str
    platform: str
    hotel: str
    streaming_url: str


class AgentProgressEventData(BaseModelForbid):
    run_id: str
    step_text: str


class AgentDoneEventData(BaseModelForbid):
    run_id: str
    offer_id: str
    status: Status


class RankingReadyEventData(BaseModelForbid):
    hero_hotel_id: str


class ErrorEventData(BaseModelForbid):
    message: str
    code: Optional[str] = None


EventData = Union[
    ParsedEventData,
    DiscoveryStartedEventData,
    ListingsFoundEventData,
    HotelsGroupedEventData,
    AgentStartedEventData,
    AgentProgressEventData,
    AgentDoneEventData,
    RankingReadyEventData,
    ErrorEventData,
]

EVENT_DATA_MODELS: dict[str, type[BaseModelForbid]] = {
    "parsed": ParsedEventData,
    "discovery_started": DiscoveryStartedEventData,
    "listings_found": ListingsFoundEventData,
    "hotels_grouped": HotelsGroupedEventData,
    "agent_started": AgentStartedEventData,
    "agent_progress": AgentProgressEventData,
    "agent_done": AgentDoneEventData,
    "ranking_ready": RankingReadyEventData,
    "error": ErrorEventData,
}


class Envelope(BaseModelForbid):
    t_ms: int
    event: Literal[
        "parsed",
        "discovery_started",
        "listings_found",
        "hotels_grouped",
        "agent_started",
        "agent_progress",
        "agent_done",
        "ranking_ready",
        "error",
    ]
    data: EventData


class ScriptFile(BaseModelForbid):
    mock: bool = True
    saved: Optional[bool] = False
    speed: Optional[float] = None
    speed_default: float = 1.0
    total_ms: int
    events: list[Envelope]
