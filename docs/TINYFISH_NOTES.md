# TinyFish SDK (v0.11.0) Integration Notes

Investigation and reference findings from introspecting `tinyfish==0.11.0`.

## 1. How a Run is Started
- Client instantiation: `c = TinyFish(api_key=os.environ["TINYFISH_API_KEY"])` (or `AsyncTinyFish`).
- Streaming execution: `c.agent.stream(url=..., goal=..., browser_profile=..., output_schema=...)`.
- Returns an `AgentStream` context manager yielding SSE event objects in real time.
- Supported profiles: `lite` (default, faster) and `stealth` (anti-bot, ~10-20% slower).
- Note: `max_steps` is a closed beta parameter on TinyFish accounts and is not exposed in standard schemas; do not rely on it.

## 2. Event Stream Lifecycle & Streaming URL
Events are emitted sequentially:
1. `STARTED`: `StartedEvent(run_id, type, timestamp)` - Run initialized.
2. `STREAMING_URL`: `StreamingUrlEvent(run_id, streaming_url, type, timestamp)` - Emitted immediately after browser allocation. This URL is passed to the UI tile (`on_stream_url`) so the user can watch the live session.
3. `PROGRESS`: `ProgressEvent(run_id, purpose, type, timestamp)` - Emitted on every browser action. The step text is held in `event.purpose`.
4. `HEARTBEAT`: `HeartbeatEvent(type, timestamp)` - Periodic ping keepalive.
5. `COMPLETE`: `CompleteEvent(run_id, status, timestamp, result_json, error)` - Run conclusion.

## 3. How the Final JSON Result Arrives
- In `CompleteEvent`, the extracted output arrives in `event.result_json`.
- `result_json` is typed as `dict[str, object] | None`. If `output_schema` is supplied, TinyFish structures the output against that JSON schema.
- Errors are provided in `event.error` (`RunError | None`).

## 4. Screenshot and Recording Retrieval (OPEN ITEM)
- **Status: NOT CONFIRMED.**
- While `CaptureConfig` allows passing `screenshots=True` and `recording=True` during run initialization, the v0.11.0 SDK provides no API endpoints or response fields to download or link screenshots or video recordings.
- `RunRetrieveResponse` (`c.runs.get(run_id)`) only exposes `streaming_url`, `status`, `goal`, `result`, and `error`.
- For the demo, `evidence` screenshots use local placeholder SVGs or captured probe assets until TinyFish adds artifact retrieval.

## 5. Steps and Cost Reporting
- Neither `CompleteEvent` nor `RunRetrieveResponse` includes explicit step counts or USD billing amounts.
- We count `ProgressEvent` occurrences during the run to determine `steps`.
- Estimated cost is calculated via `cost_usd = round(steps * 0.016, 4)` and flagged with `cost_estimated = True`.
- Wallet balance is retrieved via `c.wallet.get()`, returning `available_balance` as an ISO currency string.

## 6. Fake Mode Example (10 lines)
```python
import os, asyncio
from api.services.tinyfish import run_agent

os.environ["TINYFISH_FAKE"] = "1"
os.environ["FAKE_SPEED"] = "0.01"

async def main():
    run = await run_agent(
        url="https://www.cleartrip.com/hotels/",
        goal='Book La Marvella in Bengaluru for 20-21 Nov',
        output_schema={},
        on_stream_url=lambda url: print(f"Tile URL: {url}"),
        on_progress=lambda step: print(f"Step: {step}"),
    )
    print(f"Run ID: {run.run_id}, Status: {run.status}, Payable: {run.result.get('price_final_payable')}")

asyncio.run(main())
```
