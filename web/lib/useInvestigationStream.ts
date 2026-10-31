import { useCallback, useEffect, useReducer, useRef } from "react";

export type AgentStatus = "running" | "verified" | "unverified" | "blocked";
export type Phase = "idle" | "parsing" | "discovering" | "grouping" | "verifying" | "done" | "error";

export interface AgentState {
  runId: string;
  offerId: string;
  platform: string;
  hotel: string;
  streamingUrl: string;
  steps: number;
  stepText: string | null;
  status: AgentStatus;
}

export interface StreamState {
  phase: Phase;
  listings: number | null;
  hotels: number | null;
  error: string | null;
  /** From the error event: true means the user can retry the same search. */
  recoverable: boolean;
  agents: Record<string, AgentState>; // by run_id
}

export interface StreamEvent {
  event: string;
  data: unknown;
}

export const emptyStream: StreamState = { phase: "idle", listings: null, hotels: null, error: null, recoverable: false, agents: {} };

function rec(v: unknown): Record<string, unknown> {
  return typeof v === "object" && v !== null ? (v as Record<string, unknown>) : {};
}
const str = (v: unknown): string => (typeof v === "string" ? v : "");

/** The live API can send a different run_id on agent_done than on agent_started, so fall back to the offer. */
function agentKey(state: StreamState, d: Record<string, unknown>): string {
  const runId = str(d.run_id);
  if (runId && state.agents[runId]) return runId;
  const offerId = str(d.offer_id);
  if (offerId) {
    const hit = Object.values(state.agents).find((a) => a.offerId === offerId);
    if (hit) return hit.runId;
  }
  return "";
}

/** Pure reducer: unknown, duplicate and late events are ignored or idempotent, so the page never breaks on them. */
export function reduceStream(state: StreamState, ev: StreamEvent): StreamState {
  const d = rec(ev.data);
  const runId = str(d.run_id);
  switch (ev.event) {
    case "parsed":
      return state.phase === "idle" ? { ...state, phase: "parsing" } : state;
    case "discovery_started":
      return state.phase === "idle" || state.phase === "parsing" ? { ...state, phase: "discovering" } : state;
    case "listings_found":
      return { ...state, listings: typeof d.count === "number" ? d.count : state.listings };
    case "hotels_grouped":
      return {
        ...state,
        hotels: Array.isArray(d.hotel_groups) ? d.hotel_groups.length : state.hotels,
        phase: state.phase === "verifying" || state.phase === "done" ? state.phase : "grouping",
      };
    case "agent_started": {
      if (!runId || state.agents[runId]) return state; // duplicate start must not reset progress
      return {
        ...state,
        phase: state.phase === "done" ? "done" : "verifying",
        agents: {
          ...state.agents,
          [runId]: { runId, offerId: str(d.offer_id), platform: str(d.platform), hotel: str(d.hotel), streamingUrl: str(d.streaming_url), steps: 0, stepText: null, status: "running" },
        },
      };
    }
    case "agent_progress": {
      const key = agentKey(state, d);
      const a = key ? state.agents[key] : undefined;
      if (!a || a.status !== "running") return state;
      return { ...state, agents: { ...state.agents, [key]: { ...a, steps: a.steps + 1, stepText: str(d.step_text) || a.stepText } } };
    }
    case "agent_done": {
      const key = agentKey(state, d);
      const a = key ? state.agents[key] : undefined;
      if (!a) return state;
      const s = str(d.status);
      const status: AgentStatus = s === "verified" || s === "unverified" || s === "blocked" ? s : "unverified";
      return { ...state, agents: { ...state.agents, [key]: { ...a, status } } };
    }
    case "ranking_ready":
      return { ...state, phase: "done" };
    case "error":
      return { ...state, phase: "error", error: str(d.message) || "The investigation reported an error.", recoverable: d.recoverable === true };
    default:
      return state;
  }
}

export function replayAll(events: StreamEvent[]): StreamState {
  return events.reduce(reduceStream, emptyStream);
}

export interface Counts {
  verified: number;
  unverified: number;
  blocked: number;
  running: number;
}

/** `total` is the number of agents the run covers (offers), so running counts agents not yet finished. */
export function countsOf(state: StreamState, total: number): Counts {
  let verified = 0, unverified = 0, blocked = 0;
  for (const a of Object.values(state.agents)) {
    if (a.status === "verified") verified++;
    else if (a.status === "unverified") unverified++;
    else if (a.status === "blocked") blocked++;
  }
  return { verified, unverified, blocked, running: Math.max(0, total - verified - unverified - blocked) };
}

type Action = { type: "event"; ev: StreamEvent } | { type: "set"; state: StreamState };
function reducer(s: StreamState, a: Action): StreamState {
  return a.type === "set" ? a.state : reduceStream(s, a.ev);
}

interface Options {
  /** Show the finished run at once when the user prefers reduced motion (a replay of a recorded run). Off for real streams. */
  finalOnReducedMotion?: boolean;
}

/**
 * Drives the reducer from `open` (e.g. openStream). Starts from `initial`; `start` clears it and replays.
 */
export function useInvestigationStream(
  open: (onEvent: (event: string, data: unknown) => void) => () => void,
  initial: StreamState,
  options: Options = {},
) {
  const { finalOnReducedMotion = true } = options;
  const [state, dispatch] = useReducer(reducer, initial);
  const closeRef = useRef<(() => void) | null>(null);
  const openRef = useRef(open);
  openRef.current = open;

  const stop = useCallback(() => {
    closeRef.current?.();
    closeRef.current = null;
  }, []);

  const start = useCallback(() => {
    stop();
    if (finalOnReducedMotion && typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      dispatch({ type: "set", state: initial });
      return;
    }
    dispatch({ type: "set", state: emptyStream });
    closeRef.current = openRef.current((event, data) => dispatch({ type: "event", ev: { event, data } }));
  }, [stop, initial, finalOnReducedMotion]);

  useEffect(() => stop, [stop]);

  return { state, start, stop };
}
