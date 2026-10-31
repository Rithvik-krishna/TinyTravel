import { useCallback, useEffect, useReducer, useRef } from "react";

export type AgentStatus = "running" | "verified" | "unverified" | "blocked";

export interface AgentState {
  runId: string;
  offerId: string;
  platform: string;
  hotel: string;
  steps: number;
  stepText: string | null;
  status: AgentStatus;
}

export interface StreamState {
  agents: Record<string, AgentState>; // by run_id
}

export interface StreamEvent {
  event: string;
  data: unknown;
}

export const emptyStream: StreamState = { agents: {} };

function rec(v: unknown): Record<string, unknown> {
  return typeof v === "object" && v !== null ? (v as Record<string, unknown>) : {};
}
const str = (v: unknown): string => (typeof v === "string" ? v : "");

/** Pure reducer: unknown events are ignored, so a new event type never breaks the page. */
export function reduceStream(state: StreamState, ev: StreamEvent): StreamState {
  const d = rec(ev.data);
  const runId = str(d.run_id);
  switch (ev.event) {
    case "agent_started":
      if (!runId) return state;
      return {
        agents: {
          ...state.agents,
          [runId]: { runId, offerId: str(d.offer_id), platform: str(d.platform), hotel: str(d.hotel), steps: 0, stepText: null, status: "running" },
        },
      };
    case "agent_progress": {
      const a = state.agents[runId];
      if (!a) return state;
      return { agents: { ...state.agents, [runId]: { ...a, steps: a.steps + 1, stepText: str(d.step_text) || a.stepText } } };
    }
    case "agent_done": {
      const a = state.agents[runId];
      if (!a) return state;
      const s = str(d.status);
      const status: AgentStatus = s === "verified" || s === "unverified" || s === "blocked" ? s : "unverified";
      return { agents: { ...state.agents, [runId]: { ...a, status } } };
    }
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

/**
 * Drives the reducer from `open` (e.g. openStream). Starts from `finalState` so SSR, no-JS and
 * reduced-motion all show the finished run; `start` clears it and replays.
 */
export function useInvestigationStream(
  open: (onEvent: (event: string, data: unknown) => void) => () => void,
  finalState: StreamState,
) {
  const [state, dispatch] = useReducer(reducer, finalState);
  const closeRef = useRef<(() => void) | null>(null);
  const openRef = useRef(open);
  openRef.current = open;

  const stop = useCallback(() => {
    closeRef.current?.();
    closeRef.current = null;
  }, []);

  const start = useCallback(() => {
    stop();
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      dispatch({ type: "set", state: finalState });
      return;
    }
    dispatch({ type: "set", state: emptyStream });
    closeRef.current = openRef.current((event, data) => dispatch({ type: "event", ev: { event, data } }));
  }, [stop, finalState]);

  useEffect(() => stop, [stop]);

  return { state, start, stop };
}
