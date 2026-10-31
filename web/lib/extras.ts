"use client";

import { useEffect, useState } from "react";
import { MOCK } from "./dataSource";

// Same base-URL rule as dataSource: explicit env first, same-origin in production, localhost in dev.
const API = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

export interface GlossaryItem {
  kind: string;
  name: string;
  description: string;
  examples: string[];
}
export interface HistoryPoint {
  amount: number;
  currency: string;
  captured_at: string;
}
export interface FeeDraft {
  subject: string;
  draft_message: string;
  platform: string;
  hotel_name: string;
}

async function getJson<T>(path: string): Promise<T | null> {
  if (MOCK) return null;
  try {
    const r = await fetch(`${API}${path}`);
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

export const reportUrl = (searchId: string) => `${API}/api/search/${encodeURIComponent(searchId)}/report`;

let glossaryCache: Promise<Record<string, GlossaryItem> | null> | null = null;
/** Fee explanations by kind. Fails quietly: with no glossary the page simply shows no hints. */
export function useGlossary(): Record<string, GlossaryItem> | null {
  const [g, setG] = useState<Record<string, GlossaryItem> | null>(null);
  useEffect(() => {
    glossaryCache ??= getJson<Record<string, GlossaryItem>>("/api/fee-glossary");
    let alive = true;
    glossaryCache.then((x) => alive && setG(x));
    return () => {
      alive = false;
    };
  }, []);
  return g;
}

export function glossaryFor(g: Record<string, GlossaryItem> | null, kind?: string | null): GlossaryItem | null {
  if (!g || !kind) return null;
  return Object.values(g).find((i) => i.kind === kind) ?? null;
}

export function useHistory(hotel: string | undefined, platform: string | undefined): HistoryPoint[] | null {
  const [h, setH] = useState<HistoryPoint[] | null>(null);
  useEffect(() => {
    if (!hotel) return;
    let alive = true;
    const q = `/api/history?hotel=${encodeURIComponent(hotel)}${platform ? `&platform=${encodeURIComponent(platform)}` : ""}`;
    getJson<HistoryPoint[]>(q).then((x) => alive && setH(x));
    return () => {
      alive = false;
    };
  }, [hotel, platform]);
  return h;
}

export function fetchFeeDraft(offerId: string): Promise<FeeDraft | null> {
  return getJson<FeeDraft>(`/api/offers/${encodeURIComponent(offerId)}/report-fee-draft`);
}
/** "live" | "fake" | "mock" | "saved" from /api/health, or null when unknown (mock frontend, API down). */
export function useBackendMode(): string | null {
  const [mode, setMode] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    getJson<{ mode?: string }>("/api/health").then((h) => alive && setMode(h?.mode ?? null));
    return () => {
      alive = false;
    };
  }, []);
  return mode;
}