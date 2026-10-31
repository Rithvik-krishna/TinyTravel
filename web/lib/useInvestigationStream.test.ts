import { test } from "node:test";
import assert from "node:assert/strict";
import script from "../../fixtures/sse_script.json" with { type: "json" };
import type { StreamEvent } from "./useInvestigationStream.ts";
import { countsOf, replayAll } from "./useInvestigationStream.ts";

// Run with: node --test lib/useInvestigationStream.test.ts (Node 22.18+). vitest is not a dependency.
test("replaying the demo script ends at 6 verified, 1 unverified, 1 blocked", () => {
  const state = replayAll((script as { events: StreamEvent[] }).events);
  const c = countsOf(state, 8);
  assert.deepEqual(c, { verified: 6, unverified: 1, blocked: 1, running: 0 });
});

test("unknown events are ignored", () => {
  assert.deepEqual(replayAll([{ event: "ranking_ready", data: {} }]).agents, {});
});

test("agent_done with a different run_id still finishes the agent started for the same offer", () => {
  const state = replayAll([
    { event: "agent_started", data: { run_id: "run_h1_cleartrip", offer_id: "h1_cleartrip", platform: "cleartrip", hotel: "La Marvella", streaming_url: "" } },
    { event: "agent_started", data: { run_id: "run_h1_cleartrip", offer_id: "h1_cleartrip", platform: "cleartrip", hotel: "La Marvella", streaming_url: "" } },
    { event: "agent_progress", data: { run_id: "run_h1_cleartrip", step_text: "Select room" } },
    { event: "agent_done", data: { run_id: "0e681bb9-uuid", offer_id: "h1_cleartrip", status: "verified" } },
  ]);
  assert.equal(Object.keys(state.agents).length, 1);
  assert.equal(state.agents["run_h1_cleartrip"].status, "verified");
  assert.deepEqual(countsOf(state, 1), { verified: 1, unverified: 0, blocked: 0, running: 0 });
});

test("error event keeps the recoverable flag", () => {
  const s = replayAll([{ event: "error", data: { message: "boom", recoverable: true } }]);
  assert.equal(s.phase, "error");
  assert.equal(s.recoverable, true);
});