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

/** "20 Nov – 21 Nov · 1 night, 2 guests", or "" when the request is missing. */
export function stayLabel(r?: { check_in?: string; check_out?: string; guests?: number }): string {
  if (!r?.check_in || !r.check_out) return "";
  const f = (d: string) => new Date(`${d}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  const n = Math.round((new Date(r.check_out).getTime() - new Date(r.check_in).getTime()) / 864e5);
  const nights = n > 0 ? ` · ${n} night${n === 1 ? "" : "s"}` : "";
  const guests = r.guests ? `, ${r.guests} guest${r.guests === 1 ? "" : "s"}` : "";
  return `${f(r.check_in)} – ${f(r.check_out)}${nights}${guests}`;
}

export function hotelHref(hotelId: string, id: string | null, offer?: string): string {
  const qs = [id && `id=${encodeURIComponent(id)}`, offer && `offer=${encodeURIComponent(offer)}`].filter(Boolean).join("&");
  return `/hotel/${encodeURIComponent(hotelId)}${qs ? `?${qs}` : ""}`;
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

const MONTHS: Record<string, number> = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };

/**
 * Fills the form from a free-text sentence. A small client-side preview only: the real parser is server-side.
 * Anything it does not recognise is left unchanged.
 */
export function applySentence(r: SearchRequest, text: string, today: string): SearchRequest {
  const t = text.toLowerCase();
  const next: SearchRequest = { ...r, must_have: { ...r.must_have } };
  const city = text.split(",")[0].trim();
  if (city && city.length < 30 && !/\d/.test(city)) next.destination = city;
  const d = t.match(/(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*([a-z]{3})/);
  if (d && MONTHS[d[3]]) {
    const mo = String(MONTHS[d[3]]).padStart(2, "0");
    let year = Number((today || new Date().toLocaleDateString("en-CA")).slice(0, 4));
    const cin = (y: number) => `${y}-${mo}-${d[1].padStart(2, "0")}`;
    if (today && cin(year) < today) year += 1;
    next.check_in = cin(year);
    next.check_out = `${year}-${mo}-${d[2].padStart(2, "0")}`;
  }
  const g = t.match(/(\d+)\s*(people|guests|adults|persons)/);
  if (g) next.guests = Math.max(1, Math.min(12, Number(g[1])));
  const b = t.match(/(?:under|below|max)\s*(\d+)\s*k/);
  if (b) next.budget_per_night = Math.max(2000, Math.min(20000, Number(b[1]) * 1000));
  if (/breakfast/.test(t)) next.must_have.breakfast = true;
  if (/free cancel/.test(t)) next.must_have.free_cancellation = true;
  if (/wi-?fi/.test(t)) next.must_have.wifi = true;
  if (/parking/.test(t)) next.must_have.parking = true;
  return next;
}