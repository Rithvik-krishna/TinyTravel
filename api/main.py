import asyncio
import json
import logging
import os
from pathlib import Path
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

try:
    from .models import SearchInput, SearchResponse, ResultsResponse, HandoffPack, Recheck, SearchRequestOut
    from .services.intake import parse_request
    from .services.orchestrator import run_search, get_search_queue, get_search_results
    from .db import get_events, get_search
except ImportError:
    from models import SearchInput, SearchResponse, ResultsResponse, HandoffPack, Recheck, SearchRequestOut
    from services.intake import parse_request
    from services.orchestrator import run_search, get_search_queue, get_search_results
    from db import get_events, get_search

logger = logging.getLogger("tinytravel.api")
DATA_MODE = os.getenv("DATA_MODE", "mock")
FIX = Path(__file__).parent.parent / "fixtures"
demo = json.loads((FIX / "demo_run.json").read_text(encoding="utf-8"))
script = json.loads((FIX / "sse_script.json").read_text(encoding="utf-8"))

app = FastAPI(title="TinyTravel API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background tasks reference holder to prevent garbage collection
BACKGROUND_TASKS = set()


@app.get("/api/health")
def health():
    mode = os.getenv("DATA_MODE", "mock")
    return {"ok": True, "mode": mode}


@app.post("/api/search", response_model=SearchResponse)
async def search(body: SearchInput):
    mode = os.getenv("DATA_MODE", "mock")
    sid = uuid.uuid4().hex[:8]

    if mode == "mock":
        # Keep original mock behavior
        return {"search_id": sid}

    # DATA_MODE is "fake" or "live"
    try:
        if body.text and body.text.strip():
            parsed_req = parse_request(body.text)
            req_dict = parsed_req.model_dump()
            # Overlay any explicitly specified fields
            if body.hotel_name:
                req_dict["hotel_name"] = body.hotel_name
            if body.platforms:
                req_dict["platforms"] = body.platforms
        else:
            req_dict = body.model_dump(exclude_none=True)
            if not req_dict.get("destination"):
                req_dict["destination"] = "Bengaluru"
            if not req_dict.get("check_in"):
                req_dict["check_in"] = "2026-11-20"
            if not req_dict.get("check_out"):
                req_dict["check_out"] = "2026-11-21"

        target_info = None
        if body.hotel_name:
            target_info = {
                "hotel_name": body.hotel_name,
                "platforms": body.platforms or ["Cleartrip", "Agoda", "Booking.com"],
            }

        task = asyncio.create_task(run_search(sid, req_dict, target=target_info))
        BACKGROUND_TASKS.add(task)
        task.add_done_callback(BACKGROUND_TASKS.discard)

        return {"search_id": sid}

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start search %s: %s", sid, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate search pipeline.")


@app.get("/api/search/{sid}/stream")
async def stream(sid: str, speed: float = 1.0):
    mode = os.getenv("DATA_MODE", "mock")

    if mode == "mock":
        async def gen_mock():
            last = 0
            for ev in script["events"]:
                await asyncio.sleep(max(0, ev["t_ms"] - last) / 1000 / speed)
                last = ev["t_ms"]
                yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"
        return StreamingResponse(gen_mock(), media_type="text/event-stream")

    # Real SSE stream (fake or live) supporting late subscribers
    async def gen_live():
        # 1. Replay stored events from DB
        past_events = get_events(sid)
        replayed_count = len(past_events)
        for ev in past_events:
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"

        # Check if already completed (ranking_ready or error present)
        if any(ev["event"] in ("ranking_ready", "error") for ev in past_events):
            return

        # 2. Consume live events from queue
        queue = get_search_queue(sid)
        skipped = 0
        while True:
            item = await queue.get()
            if item is None:
                # End of stream sentinel
                break

            # Skip events that were already in the replayed batch
            if skipped < replayed_count:
                skipped += 1
                continue

            yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"

            if item.get("event") in ("ranking_ready", "error"):
                break

    return StreamingResponse(gen_live(), media_type="text/event-stream")


@app.get("/api/search/{sid}/results", response_model=ResultsResponse)
def results(sid: str):
    mode = os.getenv("DATA_MODE", "mock")
    if mode == "mock":
        return demo

    # Real results (fake or live)
    res = get_search_results(sid)
    if res:
        return res

    search_record = get_search(sid)
    if not search_record:
        raise HTTPException(status_code=404, detail="Search not found")

    if search_record.get("results"):
        return search_record["results"]

    raise HTTPException(status_code=404, detail="Results not ready")


@app.post("/api/offers/{oid}/recheck", response_model=Recheck)
def recheck(oid: str):
    # Stays mock until Prompt 8
    return demo["rechecks"][0]


@app.get("/api/offers/{oid}/handoff", response_model=HandoffPack)
def handoff(oid: str):
    # Stays mock until Prompt 8
    return demo["handoff"]
