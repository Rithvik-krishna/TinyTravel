import type { FeeLine, ResultsData } from "./tags";

/** Typed view of the parts of demo_run.json the landing page reads. Every field may be missing. */
export interface LandingMeta {
  mock?: boolean;
  saved?: boolean;
  saved_label?: string;
  saved_run_label?: string;
  label?: string;
}

export interface VerdictPick {
  cheapest_verified?: string | null;
  safe_cheapest?: string | null;
  best_for_you?: string | null;
}

export interface NonComparableWarning {
  hotel_id?: string;
  offer_id?: string;
  message?: string;
}

export interface Handoff {
  offer_id?: string;
  platform?: string;
  deep_link?: string;
  qr_png_base64?: string;
  copy_paste?: { name?: string; email?: string; phone?: string };
  disclaimer?: string;
}

export interface Recheck {
  offer_id?: string;
  message?: string;
  delta?: number | null;
  delta_pct?: number | null;
}

export interface SummaryStrip {
  listings_found?: number;
  unique_hotels?: number;
  verified?: number;
  unverified?: number;
  blocked?: number;
  avg_fee_leak_pct?: number | null;
}

export interface LandingResults extends ResultsData {
  _meta?: LandingMeta;
  summary_strip?: SummaryStrip;
  verdicts?: {
    hero_hotel_id?: string;
    per_hotel?: Record<string, VerdictPick>;
    non_comparable_warnings?: NonComparableWarning[];
  };
}

/** Provenance from _meta. `_meta` may be missing, which is treated as live (nothing shown). */
export function provenanceOf(meta: LandingMeta | undefined): { mock: boolean; label: string | null; savedLabel: string | null } {
  const mock = Boolean(meta?.mock);
  const savedLabel = meta?.saved ? meta.saved_label || meta.saved_run_label || "saved" : meta?.saved_run_label || null;
  return { mock, label: meta?.label || null, savedLabel };
}

export interface FeeGroups {
  room: FeeLine[];
  discounts: FeeLine[];
  taxes: FeeLine[];
  platform: FeeLine[];
  other: FeeLine[];
}

/**
 * Groups fee lines by label because the backend has no fee_kind yet.
 * Delete this heuristic and group on fee_kind once the contract adds it.
 */
export function groupFeeLines(lines: FeeLine[]): FeeGroups {
  const g: FeeGroups = { room: [], discounts: [], taxes: [], platform: [], other: [] };
  for (const l of lines) {
    if (l.amount < 0) g.discounts.push(l);
    else if (/tax|gst/i.test(l.label)) g.taxes.push(l);
    else if (/convenience|platform|service/i.test(l.label)) g.platform.push(l);
    else if (/room|base/i.test(l.label)) g.room.push(l);
    else g.other.push(l);
  }
  return g;
}

export function isHttpUrl(u: string | null | undefined): u is string {
  return typeof u === "string" && /^https?:\/\//i.test(u);
}

export function cancellationText(c: "free" | "partial" | "non_refundable"): string {
  return c === "free" ? "free cancellation" : c === "partial" ? "partial refund" : "non-refundable";
}
