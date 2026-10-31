import asyncio, json, os, uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

try:
    from .models import SearchInput, SearchResponse, ResultsResponse, HandoffPack, Recheck
except ImportError:
    from models import SearchInput, SearchResponse, ResultsResponse, HandoffPack, Recheck

MOCK = os.getenv("DATA_MODE", "mock") == "mock"
FIX = Path(__file__).parent.parent / "fixtures"
demo = json.loads((FIX / "demo_run.json").read_text())
script = json.loads((FIX / "sse_script.json").read_text())

app = FastAPI(title="TinyTravel API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
SEARCHES: dict[str, dict] = {}

def live_todo():
    raise HTTPException(501, "Live mode not wired yet (M1/M4). Set DATA_MODE=mock.")

@app.get("/api/health")
def health(): return {"ok": True, "mode": "mock" if MOCK else "live"}

@app.post("/api/search", response_model=SearchResponse)
def search(body: SearchInput):
    if not MOCK: live_todo()
    sid = uuid.uuid4().hex[:8]
    SEARCHES[sid] = body.model_dump(exclude_none=True)
    return {"search_id": sid}

@app.get("/api/search/{sid}/stream")
async def stream(sid: str, speed: float = 1.0):
    if not MOCK: live_todo()
    async def gen():
        last = 0
        for ev in script["events"]:
            await asyncio.sleep(max(0, ev["t_ms"] - last) / 1000 / speed)
            last = ev["t_ms"]
            yield f"event: {ev['event']}\ndata: {json.dumps(ev['data'])}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/search/{sid}/results", response_model=ResultsResponse)
def results(sid: str):
    if not MOCK: live_todo()
    return demo

@app.post("/api/offers/{oid}/recheck", response_model=Recheck)
def recheck(oid: str):
    if not MOCK: live_todo()
    return demo["rechecks"][0]

@app.get("/api/offers/{oid}/handoff", response_model=HandoffPack)
def handoff(oid: str):
    if not MOCK: live_todo()
    return demo["handoff"]
