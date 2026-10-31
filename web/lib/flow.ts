"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getResults, MOCK } from "./dataSource";
import { LandingResults } from "./landing";

export interface MustHave {
  breakfast: boolean;
  free_cancellation: boolean;
  wifi: boolean;
  parking: boolean;
}

export type DealMode = "lowest_price" | "best_value" | "most_transparent";

/** Same shape as search_request in fixtures/demo_run.json. */
export interface SearchRequest {
  destination: string;
  area_hint: string;
  check_in: string;
  check_out: string;
  guests: number;
  rooms: number;
  budget_per_night: number;
  must_have: MustHave;
  deal_mode: DealMode;
  currency: string;
  raw_text: string;
}

const REQ_KEY = "tt.lastRequest";
const ID_KEY = "tt.lastSearchId";

export function loadRequest(): SearchRequest | null {
  try {
    const raw = sessionStorage.getItem(REQ_KEY);
    return raw ? (JSON.parse(raw) as SearchRequest) : null;
  } catch {
    return null;
  }
}

export function saveSearch(req: SearchRequest, searchId: string): void {
  try {
    sessionStorage.setItem(REQ_KEY, JSON.stringify(req));
    sessionStorage.setItem(ID_KEY, searchId);
  } catch {
    /* storage unavailable: the flow still works through the URL */
  }
}

/** Search id from ?id=, else the last one this tab started, else the mock id in mock mode. Null = nothing to show. */
export function useSearchId(): { id: string | null; ready: boolean } {
  const q = useSearchParams().get("id");
  const [stored, setStored] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    try {
      setStored(sessionStorage.getItem(ID_KEY));
    } catch {
      setStored(null);
    }
    setChecked(true);
  }, []);
  const id = q ?? stored ?? (MOCK ? "mock_search" : null);
  return { id, ready: q != null || checked || MOCK };
}

export interface ResultsState {
  data: LandingResults | null;
  loading: boolean;
  error: string | null;
}

export function useResults(id: string | null, enabled = true): ResultsState {
  const [state, setState] = useState<ResultsState>({ data: null, loading: true, error: null });
  useEffect(() => {
    if (!id || !enabled) {
      setState((s) => ({ ...s, loading: false }));
      return;
    }
    let alive = true;
    setState({ data: null, loading: true, error: null });
    getResults(id)
      .then((d: LandingResults) => alive && setState({ data: d, loading: false, error: null }))
      .catch(() => alive && setState({ data: null, loading: false, error: "Couldn't load results. Try again in a moment." }));
    return () => {
      alive = false;
    };
  }, [id, enabled]);
  return state;
}

export function withId(path: string, id: string | null): string {
  return id ? `${path}?id=${encodeURIComponent(id)}` : path;
}

export const DEAL_LABEL: Record<DealMode, string> = {
  lowest_price: "Lowest price",
  best_value: "Best value",
  most_transparent: "Most transparent",
};

/** One-line sentence for the live parser, built from the structured request. */
export function buildSentence(r: SearchRequest): string {
  const must = [r.must_have.breakfast && "breakfast", r.must_have.free_cancellation && "free cancellation", r.must_have.wifi && "wifi", r.must_have.parking && "parking"].filter(Boolean);
  return [r.destination, `${r.check_in} to ${r.check_out}`, `${r.guests} ${r.guests === 1 ? "person" : "people"}`, ...must, `under ${r.budget_per_night}`].join(", ");
}
