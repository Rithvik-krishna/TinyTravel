# TinyTravel SSE Events Contract

The frontend (`web/`) consumes Server-Sent Events via `GET /api/search/:id/stream`.
Baseline script: `fixtures/sse_script.json`.

## Envelope Structure
Each SSE message is formatted as:
```
event: <event_name>
data: {"t_ms": 300, "event": "<event_name>", "data": { ... }}
```

## Normal Event Sequence & Payloads

### 1. `parsed`
- **When**: Search query is parsed from raw text into travel requirements.
- **Payload**:
  - `search_request` (`SearchRequestOut`): destination, dates, guests, rooms, must_have, deal_mode, currency, mock, raw_text.

### 2. `discovery_started`
- **When**: Parallel platform discovery kicks off.
- **Payload**:
  - `platforms` (`list[str]`): List of platform names (e.g. `["Cleartrip", "Agoda", "Booking.com"]`).

### 3. `listings_found`
- **When**: Search results pages have been scraped for listings.
- **Payload**:
  - `count` (`int`): Total listing count across platforms.
  - `by_platform` (`dict[str, int]`): Count per platform (e.g. `{"Cleartrip": 8, "Agoda": 8, "Booking.com": 8}`).

### 4. `hotels_grouped`
- **When**: Deduplication groups listings across platforms into canonical hotels.
- **Payload**:
  - `hotel_groups` (`list[HotelGroup]`): `hotel_id`, `canonical_name`, `area`, `match_status` (`merged` | `suggested`), `confidence`, `why`, `offer_ids`.

### 5. `agent_started`
- **When**: An individual checkout agent begins probing an offer.
- **Payload**:
  - `run_id` (`str`): Agent execution ID.
  - `offer_id` (`str`): Target offer ID.
  - `platform` (`str`): Platform name.
  - `hotel` (`str`): Hotel name.
  - `streaming_url` (`str`): Live agent stream URL (or mock iframe path).

### 6. `agent_progress`
- **When**: Agent advances a checkout step (room selection, guest details, etc.).
- **Payload**:
  - `run_id` (`str`): Agent execution ID.
  - `step_text` (`str`): Human-readable step description (e.g. `"Opening search page"`, `"Selecting room"`, `"Reached payment page, stopping"`).

### 7. `agent_done`
- **When**: Agent finishes its run (verified, unverified, or blocked).
- **Payload**:
  - `run_id` (`str`): Agent execution ID.
  - `offer_id` (`str`): Target offer ID.
  - `status` (`str`): `"verified"`, `"unverified"`, or `"blocked"`.

### 8. `ranking_ready`
- **When**: All agents complete, scoring is finalized, and recommendations are available.
- **Payload**:
  - `hero_hotel_id` (`str`): ID of the hero hotel to spotlight in the UI.

### 9. `error`
- **When**: Fatal error aborts pipeline or stream.
- **Payload**:
  - `message` (`str`): Human-readable error description.
  - `recoverable` (`bool`): Indicates whether the client stream or search can recover (`false` for pipeline crashes).
  - `code` (`Optional[str]`): Optional error category identifier if supplied (default: `null`).
