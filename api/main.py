import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging
import os
from pathlib import Path
from typing import Optional
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse

try:
    from .models import (
        SearchInput,
        SearchResponse,
        ResultsResponse,
        HandoffPack,
        Recheck,
        SearchRequestOut,
        PriceHistoryItem,
        FeeGlossaryItem,
        FeeDraftResponse,
        BudgetInfo,
    )
    from .services.intake import parse_request
    from .services.orchestrator import run_search, get_search_queue, get_search_results
    from .db import get_events, get_search, get_price_history, get_offer, get_total_spend
except ImportError:
    from models import (
        SearchInput,
        SearchResponse,
        ResultsResponse,
        HandoffPack,
        Recheck,
        SearchRequestOut,
        PriceHistoryItem,
        FeeGlossaryItem,
        FeeDraftResponse,
        BudgetInfo,
    )
    from services.intake import parse_request
    from services.orchestrator import run_search, get_search_queue, get_search_results
    from db import get_events, get_search, get_price_history, get_offer, get_total_spend

logger = logging.getLogger("tinytravel.api")
DATA_MODE = os.getenv("DATA_MODE", "mock")
FIX = Path(__file__).parent.parent / "fixtures"
demo = json.loads((FIX / "demo_run.json").read_text(encoding="utf-8"))
script = json.loads((FIX / "sse_script.json").read_text(encoding="utf-8"))


def _get_saved_run() -> dict:
    saved_file = FIX / "saved_run.json"
    if not saved_file.exists():
        raise HTTPException(
            status_code=503,
            detail="DATA_MODE=saved error: fixtures/saved_run.json does not exist.",
        )
    try:
        data = json.loads(saved_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DATA_MODE=saved error: failed to parse saved_run.json: {e}",
        )
    meta = data.get("_meta", {})
    if meta.get("mock") is True or meta.get("saved") is False:
        raise HTTPException(
            status_code=503,
            detail="DATA_MODE=saved error: saved_run.json contains mock data (mock: true / saved: false); a real saved run must be recorded first.",
        )
    return data


def _get_saved_script() -> dict:
    saved_script_file = FIX / "saved_sse_script.json"
    if not saved_script_file.exists():
        raise HTTPException(
            status_code=503,
            detail="DATA_MODE=saved error: fixtures/saved_sse_script.json does not exist.",
        )
    try:
        data = json.loads(saved_script_file.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DATA_MODE=saved error: failed to parse saved_sse_script.json: {e}",
        )
    if data.get("mock") is True or data.get("saved") is False:
        raise HTTPException(
            status_code=503,
            detail="DATA_MODE=saved error: saved_sse_script.json contains mock data (mock: true / saved: false); a real saved script must be recorded first.",
        )
    return data


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
    kill_switch = os.getenv("DISABLE_LIVE") == "1"
    if kill_switch and mode == "live":
        mode = "fake"
    return {"ok": True, "mode": mode, "kill_switch": kill_switch}


@app.get("/api/budget", response_model=BudgetInfo)
async def get_budget():
    max_spend = float(os.getenv("MAX_SPEND_USD", "4.0"))
    try:
        from services.tinyfish import get_balance
        balance = await get_balance()
    except Exception:
        balance = None

    try:
        spend = get_total_spend()
    except Exception:
        spend = 0.0

    status = "capped" if spend >= max_spend else "ok"
    return {
        "wallet_balance": balance,
        "spend_so_far": spend,
        "spend_cap": max_spend,
        "currency": "USD",
        "status": status,
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(body: SearchInput):
    mode = os.getenv("DATA_MODE", "mock")
    if os.getenv("DISABLE_LIVE") == "1" and mode == "live":
        logger.warning("DISABLE_LIVE=1 active: overriding live mode to fake in search")
        mode = "fake"

    sid = uuid.uuid4().hex[:8]

    if mode in ("mock", "saved"):
        if mode == "saved":
            _get_saved_run()
        # Canned modes return instant search ID
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

    if mode in ("mock", "saved"):
        curr_script = _get_saved_script() if mode == "saved" else script
        effective_speed = speed
        if mode == "saved" and speed == 1.0 and curr_script.get("speed_default"):
            effective_speed = float(curr_script["speed_default"])

        async def gen_canned():
            last = 0
            for ev in curr_script["events"]:
                await asyncio.sleep(max(0, ev["t_ms"] - last) / 1000 / effective_speed)
                last = ev["t_ms"]
                yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"
        return StreamingResponse(gen_canned(), media_type="text/event-stream")

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
    if mode == "saved":
        return _get_saved_run()

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


ROOT = Path(__file__).parent.parent
evidence_dir = ROOT / "evidence"
evidence_dir.mkdir(parents=True, exist_ok=True)
fixtures_evidence_dir = FIX / "evidence"
fixtures_evidence_dir.mkdir(parents=True, exist_ok=True)

RECHECK_SEARCH_COUNTS: dict[str, int] = {}


@app.get("/evidence/{file_path:path}")
async def serve_evidence(file_path: str):
    import urllib.parse
    # Guard against traversal, URL-encoded traversal (%2e%2e), and absolute paths
    unquoted = urllib.parse.unquote(file_path)
    if (
        ".." in unquoted
        or ".." in file_path
        or "%2e" in file_path.lower()
        or unquoted.startswith("/")
        or unquoted.startswith("\\")
        or ":" in unquoted
    ):
        raise HTTPException(status_code=404, detail="Evidence file not found")

    try:
        ev_dir_res = evidence_dir.resolve()
        p1 = (evidence_dir / unquoted).resolve()
        if p1.is_file() and p1.is_relative_to(ev_dir_res):
            return FileResponse(p1)

        fix_ev_dir_res = fixtures_evidence_dir.resolve()
        p2 = (fixtures_evidence_dir / unquoted).resolve()
        if p2.is_file() and p2.is_relative_to(fix_ev_dir_res):
            return FileResponse(p2)
    except (ValueError, RuntimeError):
        pass

    raise HTTPException(status_code=404, detail="Evidence file not found")


@app.post("/api/offers/{oid}/recheck", response_model=Recheck)
async def recheck(oid: str):
    mode = os.getenv("DATA_MODE", "mock")
    if mode == "mock" and demo.get("rechecks") and oid == demo["rechecks"][0]["offer_id"]:
        return demo["rechecks"][0]

    # Find offer to resolve search_id for recheck limit guard
    offer_obj = get_offer(oid)
    if not offer_obj:
        matched = next((o for o in demo.get("offers", []) if o.get("offer_id") == oid), None)
        if matched:
            offer_obj = matched

    sid = (offer_obj.get("search_id") if offer_obj else None) or "default_search"
    count = RECHECK_SEARCH_COUNTS.get(sid, 0)
    if count >= 2:
        raise HTTPException(
            status_code=429,
            detail=f"Recheck limit exceeded: maximum 2 rechecks allowed per search (search_id={sid}).",
        )

    if mode == "saved":
        s_run = _get_saved_run()
        for r in s_run.get("rechecks", []):
            if r.get("offer_id") == oid:
                RECHECK_SEARCH_COUNTS[sid] = count + 1
                return r
        # Canned replay recheck for saved mode offer
        off = next((o for o in s_run.get("offers", []) if o.get("offer_id") == oid), None)
        if off:
            RECHECK_SEARCH_COUNTS[sid] = count + 1
            amt = float(off.get("price_final_payable") or 11276.0)
            now_iso = datetime.now(timezone(timedelta(hours=5, minutes=30))).isoformat()
            return {
                "recheck_id": f"recheck_saved_{oid}",
                "offer_id": oid,
                "status": "done",
                "previous": {"amount": amt, "at": off.get("finished_at") or now_iso},
                "current": {"amount": amt, "at": now_iso},
                "delta": 0.0,
                "delta_pct": 0.0,
                "elapsed_minutes": 1,
                "trail_diff": [],
                "message": f"Price stable at INR {amt:,.0f} (observed in saved run).",
                "mock": False,
            }

    try:
        from agents.recheck import recheck_offer
    except ImportError:
        from .agents.recheck import recheck_offer

    try:
        res = await recheck_offer(oid)
        RECHECK_SEARCH_COUNTS[sid] = count + 1
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Recheck failed for offer {oid}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Recheck failed")


@app.get("/api/offers/{oid}/handoff", response_model=HandoffPack)
def handoff(oid: str):
    mode = os.getenv("DATA_MODE", "mock")
    if mode == "mock" and oid == demo["handoff"]["offer_id"]:
        return demo["handoff"]

    if mode == "saved":
        s_run = _get_saved_run()
        if s_run.get("handoff") and oid == s_run["handoff"].get("offer_id"):
            return s_run["handoff"]
        matched = next((o for o in s_run.get("offers", []) if o.get("offer_id") == oid), None)
        if matched:
            try:
                from services.handoff import build_handoff
            except ImportError:
                from .services.handoff import build_handoff
            return build_handoff(matched)

    try:
        from services.handoff import build_handoff
        from db import get_offer
    except ImportError:
        from .services.handoff import build_handoff
        from .db import get_offer

    offer = get_offer(oid)
    if not offer:
        matched = next((o for o in demo.get("offers", []) if o.get("offer_id") == oid), None)
        if matched:
            offer = matched

    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer '{oid}' not found")

    return build_handoff(offer)


@app.get("/api/history", response_model=list[PriceHistoryItem])
def history(
    hotel: str = Query(..., description="Canonical hotel name"),
    platform: Optional[str] = Query(None, description="Optional platform filter"),
    include_mock: bool = Query(False, description="Include mock/simulated observations"),
):
    """Retrieve historical price observations for a hotel, ordered newest first."""
    return get_price_history(hotel=hotel, platform=platform, include_mock=include_mock)



@app.get("/api/fee-glossary", response_model=dict[str, FeeGlossaryItem])
def fee_glossary():
    """Retrieve static dictionary of common travel fee explanations and kinds."""
    try:
        from services.fees import FEE_GLOSSARY
    except ImportError:
        from .services.fees import FEE_GLOSSARY
    return FEE_GLOSSARY


@app.get("/api/search/{sid}/report", response_class=HTMLResponse)
def search_report(sid: str):
    """Generate a self-contained, printable HTML evidence report."""
    mode = os.getenv("DATA_MODE", "mock")
    res = None
    if mode == "mock":
        res = demo
    else:
        res = get_search_results(sid)
        if not res:
            rec = get_search(sid)
            if rec and rec.get("results"):
                res = rec["results"]

    if not res:
        if sid in ("demo", "test", "demo_run"):
            res = demo
        else:
            raise HTTPException(status_code=404, detail=f"Search '{sid}' results not found")

    try:
        from services.reporting import generate_html_report
    except ImportError:
        from .services.reporting import generate_html_report

    return HTMLResponse(content=generate_html_report(res, search_id=sid))


@app.get("/api/offers/{oid}/report-fee-draft", response_model=FeeDraftResponse)
def report_fee_draft(oid: str):
    """Generate a polite, factual draft message for inquiring about an observed fee."""
    offer = get_offer(oid)
    if not offer:
        offer = next((o for o in demo.get("offers", []) if o.get("offer_id") == oid), None)

    if not offer:
        raise HTTPException(status_code=404, detail=f"Offer '{oid}' not found")

    try:
        from services.reporting import generate_fee_draft
    except ImportError:
        from .services.reporting import generate_fee_draft

    return generate_fee_draft(offer)

