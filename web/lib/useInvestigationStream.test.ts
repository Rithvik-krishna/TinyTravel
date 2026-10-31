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
