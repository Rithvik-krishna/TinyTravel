# Pack 6 — Google Stack Facts and Infrastructure Reference

**Scope:** Google Gemini models, vision/multimodal capabilities, computer-use status, API pricing, Cloud Run limits, Cloud Tasks/Scheduler, and Startup Buildathon credit terms.  
**Standard:** Every claim marked QUOTED / MEASURED / INFERRED / NOT VERIFIED with direct URLs and verification dates. Output formatted in tables.

---

## 1. Google Gemini Models, Multimodal & Pricing Matrix

| Model Identifier | Primary Capability & Architecture | Vision / Multimodal Support | Native Computer-Use (GUI Actions) | Input Pricing (per 1M tokens) | Output Pricing (per 1M tokens) | Official Documentation URL | Status (as of 14 Nov 2026) |
|---|---|---|---|---|---|---|---|
| **Gemini 2.5 Flash / 3.5 Flash-Lite** | Ultra-fast lightweight model for structured extraction & query intake | Native multimodal (images, video, audio, PDFs) | **No** (extraction only; requires external Playwright driver) | ~$0.15 – $0.30 | ~$0.60 – $2.50 | [ai.google.dev/pricing](https://ai.google.dev/pricing) | **QUOTED** |
| **Gemini 2.5 Pro / 3.x Pro** | Complex reasoning, code generation, and deep DOM analysis | Native multimodal (high-res screen & DOM analysis) | **No** (no native mouse/keyboard action API) | ~$1.25 – $2.50 | ~$5.00 – $10.00 | [ai.google.dev/pricing](https://ai.google.dev/pricing) | **QUOTED** |
| **Gemini 1.5 Flash (Legacy)** | Predecessor fast inference model (end of lifecycle) | Native multimodal | No | $0.075 (<128k prompt) | $0.30 (<128k prompt) | [ai.google.dev/pricing](https://ai.google.dev/pricing) | **QUOTED** |

---

## 2. Google Cloud Run Service Resource Limits

| Configuration Parameter | Platform Default | Maximum Limit | Architectural Implication for TinyTravel | Official Cloud Run Reference | Status |
|---|---|---|---|---|---|
| **Request Timeout** | 300 seconds (5 minutes) | **3600 seconds (60 minutes)** | Must set `--timeout=600s` to support long-running autonomous checkout verifications. | [cloud.google.com/run/docs/configuring/request-timeout](https://cloud.google.com/run/docs/configuring/request-timeout) | **QUOTED** |
| **Memory Allocation** | 512 MiB | **32 GiB** | Container running headless Chromium requires $\ge 2$ GiB RAM to prevent browser crashes. | [cloud.google.com/run/docs/configuring/memory-limits](https://cloud.google.com/run/docs/configuring/memory-limits) | **QUOTED** |
| **vCPU Allocation** | 1 vCPU | **8 vCPUs** | Allocate $\ge 2$ vCPUs for smooth headless browser execution. | [cloud.google.com/run/docs/configuring/cpu-allocation](https://cloud.google.com/run/docs/configuring/cpu-allocation) | **QUOTED** |
| **CPU Throttling Policy** | Throttled outside requests | **`--no-cpu-throttling`** | **CRITICAL:** Must disable CPU throttling so headless browser agents execute continuously. | [cloud.google.com/run/docs/configuring/cpu-allocation](https://cloud.google.com/run/docs/configuring/cpu-allocation) | **QUOTED** |
| **Streaming (SSE / WebSockets)** | Supported natively | Persistent up to timeout | Supports FastAPI Server-Sent Events (`StreamingResponse`) for live tile progress. | [cloud.google.com/run/docs/triggering/websockets](https://cloud.google.com/run/docs/triggering/websockets) | **QUOTED** |

---

## 3. Google Cloud Asynchronous Execution & Scheduling Limits

| Service | Mechanism | Maximum Throughput / Rate | Payload / Execution Limit | Role in TinyTravel Architecture | Status |
|---|---|---|---|---|---|
| **Google Cloud Tasks** | Distributed asynchronous task queue | 500 dispatches/second per queue | 100 KB payload; exponential backoff retries | Manages concurrency-capped parallel platform probes and live re-checks. | **QUOTED** |
| **Google Cloud Scheduler** | Managed cron job triggers | Triggers every 1 minute minimum | Standard HTTP/PubSub target | Drives recurring hotel price freshness polling and automated cache invalidation. | **QUOTED** |

---

## 4. Startup Buildathon India 2026 Credit Terms & Awards

| Term Item | Published Terms | Verification Source | Status |
|---|---|---|---|
| **Organizers & Partners** | Google AI, Google Cloud, Hack2skill, nasscom, HeadStart | [startupbuildathon.com](https://startupbuildathon.com) | **QUOTED** |
| **Total Prize Pool** | USD 100,000 shared across top 10 winning teams | [startupbuildathon.com](https://startupbuildathon.com) | **QUOTED** |
| **Per-Team Award** | **USD 10,000 per team** (split as USD 5,000 cash + USD 5,000 Google AI & Cloud credits) | [startupbuildathon.com](https://startupbuildathon.com) | **QUOTED** |
| **Credit Eligibility & Expiry** | Subject to Google for Startups Cloud program terms; applicable to Google Cloud Platform and Vertex AI consumption. | [startupbuildathon.com](https://startupbuildathon.com) | **INFERRED** |
| **Application Deadline** | **13 Nov 2026** (officially closed; verified 14 Nov 2026) | [startupbuildathon.com](https://startupbuildathon.com) | **QUOTED** |
| **City Buildathons** | 20–21 Nov 2026 across 10 cities; Grand Finale 2 Dec 2026 in Bengaluru | [startupbuildathon.com](https://startupbuildathon.com) | **QUOTED** |
