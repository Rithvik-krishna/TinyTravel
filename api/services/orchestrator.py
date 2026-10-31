"""Orchestrator Service for TinyTravel pipeline.
Coordinates: Intake -> Discovery -> Deduplication -> Target Selection -> Checkout Verification -> Scoring -> SSE/Results.
"""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
import os
import time
from typing import Optional, Union, Any

try:
    from ..models import (
        SearchRequestOut,
        ResultsResponse,
        HotelGroup,
        Hotel,
        Listing,
        Offer,
        Verdicts,
        VerdictPick,
        RankingItem,
        NonComparableWarning,
        SummaryStrip,
        TravelProfile,
        MetaInfo,
        HandoffPack,
        SelectionCard,
        CopyPastePack,
    )
    from ..events import (
        Envelope,
        ParsedEventData,
        DiscoveryStartedEventData,
        ListingsFoundEventData,
        HotelsGroupedEventData,
        AgentStartedEventData,
        AgentProgressEventData,
        AgentDoneEventData,
        RankingReadyEventData,
        ErrorEventData,
    )
    from ..db import (
        save_search,
        update_search,
        get_search,
        append_event,
        get_events,
        save_offer,
        save_price_history,
    )
    from ..agents.discovery import discover
    from ..agents.checkout import verify_offer
    from .dedupe import group_listings, normalize_name
    from .normalize import select_targets, non_comparable_warnings
    from .scoring import rank_offers, pick_verdicts, summary_strip, transparency_score


except ImportError:
    from models import (
        SearchRequestOut,
        ResultsResponse,
        HotelGroup,
        Hotel,
        Listing,
        Offer,
        Verdicts,
        VerdictPick,
        RankingItem,
        NonComparableWarning,
        SummaryStrip,
        TravelProfile,
        MetaInfo,
        HandoffPack,
        SelectionCard,
        CopyPastePack,
    )
    from events import (
        Envelope,
        ParsedEventData,
        DiscoveryStartedEventData,
        ListingsFoundEventData,
        HotelsGroupedEventData,
        AgentStartedEventData,
        AgentProgressEventData,
        AgentDoneEventData,
        RankingReadyEventData,
        ErrorEventData,
    )
    from db import (
        save_search,
        update_search,
        get_search,
        append_event,
        get_events,
        save_offer,
        save_price_history,
    )
    from agents.discovery import discover
    from agents.checkout import verify_offer
    from services.dedupe import group_listings, normalize_name
    from services.normalize import select_targets, non_comparable_warnings
    from services.scoring import rank_offers, pick_verdicts, summary_strip, transparency_score

from rapidfuzz import fuzz


logger = logging.getLogger("tinytravel.orchestrator")
IST = timezone(timedelta(hours=5, minutes=30))

# In-memory queues for active SSE connections
SEARCH_QUEUES: dict[str, asyncio.Queue] = {}
# In-memory partial/complete results cache
ACTIVE_RESULTS: dict[str, dict] = {}


def get_search_queue(search_id: str) -> asyncio.Queue:
    """Get or create an asyncio.Queue for streaming SSE events for a search."""
    if search_id not in SEARCH_QUEUES:
        SEARCH_QUEUES[search_id] = asyncio.Queue()
    return SEARCH_QUEUES[search_id]


def get_search_results(search_id: str) -> Optional[dict]:
    """Retrieve in-memory or database results for a search."""
    if search_id in ACTIVE_RESULTS:
        return ACTIVE_RESULTS[search_id]
    rec = get_search(search_id)
    if rec and rec.get("results"):
        return rec["results"]
    return None


async def emit_event(search_id: str, event_name: str, data: dict, start_time: float) -> None:
    """Emit an SSE event to the in-memory queue and persist to DB event log."""
    t_ms = int((time.monotonic() - start_time) * 1000)
    append_event(search_id, t_ms, event_name, data)

    queue = get_search_queue(search_id)
    payload = {
        "t_ms": t_ms,
        "event": event_name,
        "data": data,
    }
    await queue.put(payload)


def _create_unverified_offer(
    offer_id: str,
    hotel_id: str,
    hotel_name: str,
    platform: str,
    run_id: str,
    blocker: str = "other",
    furthest_step: str = "failed",
    notes: str = "",
    mock: bool = False,
) -> dict:
    now_iso = datetime.now(IST).isoformat()
    return {
        "offer_id": offer_id,
        "hotel_id": hotel_id,
        "run_id": run_id,
        "streaming_url": None,
        "started_at": now_iso,
        "finished_at": now_iso,
        "steps": 0,
        "cost_usd": 0.0,
        "status": "unverified",
        "reconciliation": None,
        "cancellation_category": None,
        "site": platform,
        "reached_payment_page": False,
        "furthest_step": furthest_step,
        "blocker": blocker,
        "hotel_name": hotel_name,
        "hotel_url": "",
        "room_type": "",
        "max_occupancy": 2,
        "meal_plan": "",
        "cancellation_policy": "",
        "price_shown_on_listing": None,
        "price_shown_on_room_selection": None,
        "price_final_payable": None,
        "fee_lines": [],
        "preselected_addons": [],
        "urgency_or_scarcity_messages": [],
        "price_trail": [],
        "currency": "INR",
        "notes": notes,
        "fee_leak_pct": None,
        "evidence": [],
        "mock": mock,
        "transparency": {
            "score": None,
            "breakdown": None,
            "note": "N/A (not verified)",
        },
    }


def _build_handoff_pack(best_offer: Optional[dict], req_dict: dict, mock: bool = False) -> dict:
    """Construct a HandoffPack adhering to the contract via handoff service."""
    try:
        from services.handoff import build_handoff
    except ImportError:
        from .handoff import build_handoff

    offer_to_use = dict(best_offer) if best_offer else {
        "offer_id": "h1_cleartrip",
        "hotel_name": "La Marvella",
        "site": "Cleartrip",
        "hotel_url": "https://www.cleartrip.com",
        "price_final_payable": 7420.0,
        "mock": mock,
    }
    return build_handoff(offer_to_use, req_dict)


async def run_search(
    search_id: str,
    request: Union[dict, SearchRequestOut, Any],
    target: Optional[dict] = None,
) -> dict:
    """Execute end-to-end search pipeline."""
    start_time = time.monotonic()
    queue = get_search_queue(search_id)

    # 1. Normalize request input
    if hasattr(request, "model_dump"):
        req_dict = request.model_dump(exclude_none=True)
    elif isinstance(request, dict):
        req_dict = dict(request)
    else:
        req_dict = {}

    is_mock = os.getenv("DATA_MODE", "live") == "fake" or req_dict.get("mock", False) or os.getenv("TINYFISH_FAKE") == "1"
    req_dict["mock"] = is_mock

    # Format search request model for event
    search_req_out = SearchRequestOut(
        destination=req_dict.get("destination", "Bengaluru"),
        area_hint=req_dict.get("area_hint"),
        check_in=req_dict.get("check_in", "2026-11-20"),
        check_out=req_dict.get("check_out", "2026-11-21"),
        guests=int(req_dict.get("guests", 2)),
        rooms=int(req_dict.get("rooms", 1)),
        budget_per_night=req_dict.get("budget_per_night"),
        must_have=req_dict.get("must_have", {}),
        deal_mode=req_dict.get("deal_mode", "best_value"),
        currency=req_dict.get("currency", "INR"),
        mock=is_mock,
        raw_text=req_dict.get("raw_text") or req_dict.get("text"),
    )

    save_search(search_id, search_req_out.model_dump(), status="running")

    # Initial partial results
    ACTIVE_RESULTS[search_id] = {
        "_meta": {"mock": is_mock, "label": "live" if not is_mock else "mock", "note": "Search in progress"},
        "search_request": search_req_out.model_dump(),
        "travel_profile": {
            "traveller_type": "couple" if search_req_out.guests == 2 else ("solo" if search_req_out.guests == 1 else "friends"),
            "hotel_type": "any",
            "must_have": [k for k, v in search_req_out.must_have.items() if v],
            "prefers_refundable": search_req_out.must_have.get("free_cancellation", True),
            "deal_mode": search_req_out.deal_mode,
        },
        "hotels": [],
        "listings": [],
        "hotel_groups": [],
        "offers": [],
        "verdicts": {
            "deal_mode": search_req_out.deal_mode,
            "hero_hotel_id": "h1",
            "overall": {},
            "per_hotel": {},
            "ranking": [],
            "non_comparable_warnings": [],
            "mock": is_mock,
        },
        "handoff": _build_handoff_pack(None, req_dict, mock=is_mock),
        "rechecks": [],
        "summary_strip": {
            "listings_found": 0,
            "unique_hotels": 0,
            "verified": 0,
            "unverified": 0,
            "blocked": 0,
            "avg_fee_leak_pct": None,
        },
        "complete": False,
    }

    try:
        # Event 1: parsed
        await emit_event(
            search_id,
            "parsed",
            {"search_request": search_req_out.model_dump()},
            start_time,
        )

        # 2. Check Target Mode
        is_target_mode = bool(
            target
            or req_dict.get("hotel_name")
            or (target and target.get("hotel_name"))
        )

        all_listings: list[dict] = []
        hotel_groups: list[dict] = []
        target_offers_to_run: list[dict] = []

        if is_target_mode:
            # TARGET MODE: Run checkout directly for 1 hotel across specified platforms
            target_hotel = req_dict.get("hotel_name") or (target or {}).get("hotel_name", "La Marvella")
            platforms = req_dict.get("platforms") or (target or {}).get("platforms") or ["Cleartrip", "Agoda", "Booking.com"]

            # Map platforms to canonical offer_ids
            offer_ids = []
            for p in platforms:
                pslug = p.lower().replace(".", "").replace(" ", "")
                if pslug == "bookingcom":
                    pslug = "booking"
                offer_ids.append(f"h1_{pslug}")

            # Emit synthetic grouped hotel event for the target
            h_group = {
                "hotel_id": "h1",
                "canonical_name": target_hotel,
                "area": req_dict.get("area_hint") or "HSR Layout",
                "match_status": "merged",
                "confidence": 0.96,
                "why": "Target mode: single hotel across platforms",
                "offer_ids": offer_ids,
            }
            hotel_groups = [h_group]
            await emit_event(
                search_id,
                "hotels_grouped",
                {"hotel_groups": hotel_groups},
                start_time,
            )

            for p, oid in zip(platforms, offer_ids):
                target_offers_to_run.append({
                    "platform": p,
                    "hotel_name": target_hotel,
                    "offer_id": oid,
                    "hotel_id": "h1",
                    "listing": None,
                })

        else:
            # DISCOVERY MODE: Full search
            platforms = ["Cleartrip", "Agoda", "Booking.com"]

            # Event 2: discovery_started
            await emit_event(
                search_id,
                "discovery_started",
                {"platforms": platforms},
                start_time,
            )

            # Discover listings across platforms in parallel, limited by semaphore
            max_concurrent = int(os.getenv("MAX_CONCURRENT_RUNS", "3"))
            discovery_semaphore = asyncio.Semaphore(max_concurrent)

            async def run_discovery_one(platform_name: str) -> list[dict]:
                async with discovery_semaphore:
                    try:
                        return await discover(platform_name, req_dict)
                    except Exception as exc:
                        logger.warning("Discovery failed for %s: %s", platform_name, exc)
                        return []

            discovery_results = await asyncio.gather(
                *(run_discovery_one(p) for p in platforms),
                return_exceptions=False,
            )

            by_platform_count = {}
            for p, res_listings in zip(platforms, discovery_results):
                by_platform_count[p] = len(res_listings)
                all_listings.extend(res_listings)

            # Event 3: listings_found
            await emit_event(
                search_id,
                "listings_found",
                {
                    "count": len(all_listings),
                    "by_platform": by_platform_count,
                },
                start_time,
            )

            # Deduplication
            hotel_groups = group_listings(all_listings)

            # Event 4: hotels_grouped
            await emit_event(
                search_id,
                "hotels_grouped",
                {"hotel_groups": hotel_groups},
                start_time,
            )

            # Target Selection
            budget_limit = req_dict.get("budget_per_night")
            target_groups = select_targets(
                hotel_groups,
                max_hotels=3,
                budget_per_night=budget_limit,
                listings=all_listings,
            )

            # If no multi-platform groups qualified, take top groups
            if not target_groups and hotel_groups:
                target_groups = hotel_groups[:1]

            # Build list of offers to probe
            probe_missing = os.getenv("PROBE_MISSING", "0") == "1"

            for g in target_groups:
                gid = g["hotel_id"]
                hname = g["canonical_name"]
                for oid in g.get("offer_ids", []):
                    # Extract platform from offer_id (e.g. h1_cleartrip -> Cleartrip)
                    pslug = oid.split("_", 1)[1] if "_" in oid else "cleartrip"
                    if pslug == "booking":
                        platform_name = "Booking.com"
                    elif pslug == "agoda":
                        platform_name = "Agoda"
                    else:
                        platform_name = "Cleartrip"

                    # Find matching listing if available
                    pslug_norm = pslug.lower().replace(".", "").replace(" ", "")
                    valid_platforms = {"booking", "bookingcom"} if pslug_norm == "booking" else {pslug_norm}

                    matched_listing = next(
                        (
                            l for l in all_listings
                            if l.get("platform", "").lower().replace(".", "").replace(" ", "") in valid_platforms
                            and (
                                l.get("hotel_name", "").lower() == hname.lower()
                                or fuzz.token_sort_ratio(normalize_name(l.get("hotel_name", "")), normalize_name(hname)) >= 80
                            )
                        ),
                        None,
                    )

                    # Config PROBE_MISSING=0: skip platforms where the hotel wasn't discovered
                    if not probe_missing and matched_listing is None:
                        continue

                    target_offers_to_run.append({
                        "platform": platform_name,
                        "hotel_name": hname,
                        "offer_id": oid,
                        "hotel_id": gid,
                        "listing": matched_listing,
                    })


        # 3. Checkout Verification Phase
        max_concurrent = int(os.getenv("MAX_CONCURRENT_RUNS", "3"))
        semaphore = asyncio.Semaphore(max_concurrent)
        max_spend_usd = float(os.getenv("MAX_SPEND_USD", "4.0"))
        per_run_timeout_s = int(os.getenv("AGENT_TIMEOUT_S", "360"))

        cumulative_spend_usd = 0.0
        spend_lock = asyncio.Lock()
        probed_offers: list[dict] = []

        async def run_checkout_task(item: dict) -> dict:
            nonlocal cumulative_spend_usd
            platform_name = item["platform"]
            hotel_name = item["hotel_name"]
            offer_id = item["offer_id"]
            hotel_id = item["hotel_id"]
            run_id = f"mock_run_{offer_id}" if is_mock else f"run_{offer_id}"

            # Budget guard check
            async with spend_lock:
                if cumulative_spend_usd >= max_spend_usd:
                    # Skip run and emit agent_done status unverified
                    await emit_event(
                        search_id,
                        "agent_done",
                        {"run_id": run_id, "offer_id": offer_id, "status": "unverified"},
                        start_time,
                    )
                    unverified_offer = _create_unverified_offer(
                        offer_id=offer_id,
                        hotel_id=hotel_id,
                        hotel_name=hotel_name,
                        platform=platform_name,
                        run_id=run_id,
                        blocker="other",
                        furthest_step="skipped",
                        notes="Skipped: MAX_SPEND_USD limit reached",
                        mock=is_mock,
                    )
                    return unverified_offer

            async with semaphore:
                # Callbacks for streaming events
                async def on_stream_url(stream_url: str):
                    await emit_event(
                        search_id,
                        "agent_started",
                        {
                            "run_id": run_id,
                            "offer_id": offer_id,
                            "platform": platform_name,
                            "hotel": hotel_name,
                            "streaming_url": stream_url,
                        },
                        start_time,
                    )

                async def on_progress(step_text: str):
                    await emit_event(
                        search_id,
                        "agent_progress",
                        {
                            "run_id": run_id,
                            "step_text": step_text,
                        },
                        start_time,
                    )

                offer_req = dict(req_dict)
                offer_req["offer_id"] = offer_id
                offer_req["hotel_id"] = hotel_id
                offer_req["timeout_s"] = per_run_timeout_s

                try:
                    offer_res = await asyncio.wait_for(
                        verify_offer(
                            platform=platform_name,
                            hotel_name=hotel_name,
                            req=offer_req,
                            on_stream_url=on_stream_url,
                            on_progress=on_progress,
                        ),
                        timeout=per_run_timeout_s + 10,
                    )
                except Exception as exc:
                    logger.warning("Agent execution failed for %s on %s: %s", hotel_name, platform_name, exc)
                    try:
                        from agents.checkout import classify_blocker
                    except ImportError:
                        from .agents.checkout import classify_blocker
                    b_val = "timeout" if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) else (classify_blocker(str(exc)) or "other")
                    offer_res = _create_unverified_offer(
                        offer_id=offer_id,
                        hotel_id=hotel_id,
                        hotel_name=hotel_name,
                        platform=platform_name,
                        run_id=run_id,
                        blocker=b_val,
                        furthest_step="timeout" if b_val == "timeout" else "failed",
                        notes=f"Run failed: {exc}",
                        mock=is_mock,
                    )

                # Update spend
                cost = float(offer_res.get("cost_usd") or 0.0)
                async with spend_lock:
                    cumulative_spend_usd += cost

                # Emit agent_done
                actual_status = offer_res.get("status", "unverified")
                actual_run_id = offer_res.get("run_id") or run_id
                await emit_event(
                    search_id,
                    "agent_done",
                    {
                        "run_id": actual_run_id,
                        "offer_id": offer_id,
                        "status": actual_status,
                    },
                    start_time,
                )

                # Persist verified offer and write to price_history
                save_offer(offer_id, search_id, offer_res)
                if actual_status == "verified" and offer_res.get("price_final_payable") is not None:
                    save_price_history(
                        hotel=hotel_name,
                        platform=platform_name,
                        amount=float(offer_res["price_final_payable"]),
                        captured_at=offer_res.get("finished_at") or datetime.now(IST).isoformat(),
                        offer_id=offer_id,
                    )

                return offer_res

        # Run checkout agents concurrently
        if target_offers_to_run:
            results = await asyncio.gather(
                *(run_checkout_task(item) for item in target_offers_to_run),
                return_exceptions=False,
            )
            probed_offers.extend(results)

        # 4. Final Scoring, Ranking, Verdicts, and Response Assembly
        # Build Hotels list
        hotel_map = {}
        for g in hotel_groups:
            hid = g["hotel_id"]
            if hid not in hotel_map:
                hotel_map[hid] = {
                    "hotel_id": hid,
                    "canonical_name": g["canonical_name"],
                    "area": g["area"],
                    "rating": 4.5,
                }
        hotels_list = list(hotel_map.values())

        deal_mode = req_dict.get("deal_mode", "best_value")
        ranking = rank_offers(probed_offers, hotels_list, deal_mode=deal_mode)
        verdicts_data = pick_verdicts(probed_offers, ranking)
        warnings_data = non_comparable_warnings(probed_offers)
        summary_data = summary_strip(probed_offers, listings=len(all_listings))

        # Hero hotel is top ranked hotel or overall best_for_you hotel
        hero_hotel_id = "h1"
        if ranking:
            top_oid = ranking[0]["offer_id"]
            top_o = next((o for o in probed_offers if o.get("offer_id") == top_oid), None)
            if top_o and top_o.get("hotel_id"):
                hero_hotel_id = top_o["hotel_id"]
        elif hotel_groups:
            hero_hotel_id = hotel_groups[0]["hotel_id"]

        # Reformat verdicts object to match Verdicts schema
        verdicts_obj = {
            "deal_mode": deal_mode,
            "hero_hotel_id": hero_hotel_id,
            "ranking": ranking,
            "overall": verdicts_data.get("overall", {}),
            "per_hotel": verdicts_data.get("per_hotel", {}),
            "non_comparable_warnings": warnings_data,
            "mock": is_mock,
        }

        # Best offer for handoff pack
        best_oid = verdicts_data.get("best_for_you") or (ranking[0]["offer_id"] if ranking else None)
        best_offer = next((o for o in probed_offers if o.get("offer_id") == best_oid), None)
        if not best_offer and probed_offers:
            best_offer = probed_offers[0]
        handoff_obj = _build_handoff_pack(best_offer, req_dict, mock=is_mock)

        # Convert listings to strict Listing dicts if needed
        clean_listings = []
        for l in all_listings:
            clean_listings.append({
                "listing_id": l.get("listing_id", "lst_001"),
                "platform": l.get("platform", "Cleartrip"),
                "hotel_name": l.get("hotel_name", ""),
                "address": l.get("address"),
                "area": l.get("area"),
                "lat": l.get("lat"),
                "lng": l.get("lng"),
                "phone": l.get("phone"),
                "rating": l.get("rating"),
                "shown_price": l.get("shown_price"),
                "currency": l.get("currency", "INR"),
                "source_url": l.get("source_url", ""),
                "captured_at": l.get("captured_at") or datetime.now(IST).isoformat(),
                "mock": is_mock,
            })

        final_response_dict = {
            "_meta": {
                "mock": is_mock,
                "label": "live" if not is_mock else "mock",
                "note": "Complete run",
            },
            "search_request": search_req_out.model_dump(),
            "travel_profile": {
                "traveller_type": "couple" if search_req_out.guests == 2 else ("solo" if search_req_out.guests == 1 else "friends"),
                "hotel_type": "any",
                "must_have": [k for k, v in search_req_out.must_have.items() if v],
                "prefers_refundable": search_req_out.must_have.get("free_cancellation", True),
                "deal_mode": deal_mode,
            },
            "hotels": hotels_list,
            "listings": clean_listings,
            "hotel_groups": hotel_groups,
            "offers": probed_offers,
            "verdicts": verdicts_obj,
            "handoff": handoff_obj,
            "rechecks": [],
            "summary_strip": summary_data,
            "complete": True,
        }

        # Validate with strict Pydantic model
        ResultsResponse.model_validate(final_response_dict)

        ACTIVE_RESULTS[search_id] = final_response_dict
        update_search(search_id, status="completed", results=final_response_dict)

        # Event: ranking_ready
        await emit_event(
            search_id,
            "ranking_ready",
            {"hero_hotel_id": hero_hotel_id},
            start_time,
        )

        return final_response_dict

    except Exception as exc:
        logger.error("Search pipeline error: %s", exc, exc_info=True)
        await emit_event(
            search_id,
            "error",
            {"message": str(exc), "recoverable": False},
            start_time,
        )
        update_search(search_id, status="error")
        raise
    finally:
        # Sentinel to end SSE stream
        await queue.put(None)
