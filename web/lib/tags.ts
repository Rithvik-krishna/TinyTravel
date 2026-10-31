export interface FeeLine {
  label: string;
  amount: number;
}

export interface PriceTrailItem {
  step: string;
  amount: number;
  currency?: string;
}

export interface EvidenceItem {
  type: string;
  url: string;
  step: string;
  captured_at: string;
  extracted_value: number;
  currency: string;
  mock?: boolean;
}

export interface TagItem {
  id: string; // offer_id
  title: string; // hotel_name
  platform: string; // site
  listing: number | null; // price_shown_on_listing
  payable: number | null; // price_final_payable (may be null)
  status: "verified" | "unverified" | "blocked";
  blocker: string | null;
  cancellation_category: "free" | "partial" | "non_refundable";
  fee_leak_pct: number | null;
  fee_lines: FeeLine[];
  price_trail: PriceTrailItem[];
  urgency_or_scarcity_messages: string[];
  preselected_addons: unknown[];
  transparency: unknown;
  verifiedAt: string | null; // finished_at
  hotelId: string; // hotel_id
  matchStatus: string; // from hotel_groups ("merged" | "suggested" | etc.)
  groupName?: string;
  groupConfidence?: number;
  groupWhy?: string;
  groupArea?: string;
  aspect: number; // fixed ~0.62 portrait tag
  drop: number; // scaled fee_leak_pct (0 to 0.3), null leak = 0. Longer string = bigger leak.
  evidence?: EvidenceItem[];
  room_type?: string;
  meal_plan?: string;
  cancellation_policy?: string;
  hotel_url?: string;
  reconciliation?: string;
  notes?: string;
  mock?: boolean;
}

export interface ResultsData {
  _meta?: unknown;
  offers?: unknown[];
  hotel_groups?: Array<{
    hotel_id?: string;
    canonical_name?: string;
    area?: string;
    match_status?: string;
    confidence?: number;
    why?: string;
    offer_ids?: string[];
  }>;
  summary_strip?: unknown;
  handoff?: unknown;
  rechecks?: unknown[];
}

const BLOCKER_LABEL: Record<string, string> = {
  captcha: "Stopped at captcha",
  login: "Stopped at login",
  otp: "Stopped at OTP",
  timeout: "Stopped at room step",
  other: "Stopped before payment",
};

/** Plain reason shown on a blocked tag. Unknown blocker is still stated, never hidden. */
export function blockerLabel(blocker: string | null | undefined): string {
  return (blocker && BLOCKER_LABEL[blocker]) || "Stopped before payment";
}

function computeDrop(feeLeakPct: number | null | undefined): number {
  if (feeLeakPct == null || feeLeakPct <= 0 || isNaN(feeLeakPct)) {
    return 0;
  }
  // Scale fee_leak_pct (0..50%+) linearly into 0..0.3
  const scaled = (feeLeakPct / 50) * 0.3;
  return Math.min(0.3, Math.max(0, Math.round(scaled * 1000) / 1000));
}

export function offersToTags(results: ResultsData | unknown[] | null | undefined): TagItem[] {
  if (!results) return [];

  const rawOffers: Array<Record<string, unknown>> = Array.isArray(results)
    ? (results as Array<Record<string, unknown>>)
    : Array.isArray((results as ResultsData).offers)
    ? ((results as ResultsData).offers as Array<Record<string, unknown>>)
    : [];

  const hotelGroups = !Array.isArray(results) && Array.isArray((results as ResultsData).hotel_groups)
    ? (results as ResultsData).hotel_groups!
    : [];

  const offerGroupMap = new Map<string, NonNullable<(typeof hotelGroups)[number]>>();
  const hotelGroupMap = new Map<string, NonNullable<(typeof hotelGroups)[number]>>();

  for (const group of hotelGroups) {
    if (group.hotel_id) {
      hotelGroupMap.set(group.hotel_id, group);
    }
    if (Array.isArray(group.offer_ids)) {
      for (const oid of group.offer_ids) {
        offerGroupMap.set(oid, group);
      }
    }
  }

  return rawOffers.map((offer): TagItem => {
    const offerId = String(offer.offer_id ?? "");
    const hotelId = String(offer.hotel_id ?? "");
    const group = offerGroupMap.get(offerId) || hotelGroupMap.get(hotelId);
    const matchStatus = group?.match_status || "merged";
    const leak = typeof offer.fee_leak_pct === "number" ? offer.fee_leak_pct : null;

    return {
      id: offerId,
      title: String(offer.hotel_name || "Hotel"),
      platform: String(offer.site || "Platform"),
      listing: typeof offer.price_shown_on_listing === "number" ? offer.price_shown_on_listing : null,
      payable: typeof offer.price_final_payable === "number" ? offer.price_final_payable : null,
      status: (offer.status as "verified" | "unverified" | "blocked") || "unverified",
      blocker: offer.blocker ? String(offer.blocker) : null,
      cancellation_category: (offer.cancellation_category as "free" | "partial" | "non_refundable") || "free",
      fee_leak_pct: leak,
      fee_lines: Array.isArray(offer.fee_lines) ? (offer.fee_lines as FeeLine[]) : [],
      price_trail: Array.isArray(offer.price_trail) ? (offer.price_trail as PriceTrailItem[]) : [],
      urgency_or_scarcity_messages: Array.isArray(offer.urgency_or_scarcity_messages)
        ? (offer.urgency_or_scarcity_messages as string[])
        : [],
      preselected_addons: Array.isArray(offer.preselected_addons) ? (offer.preselected_addons as unknown[]) : [],
      transparency: offer.transparency ?? null,
      verifiedAt: offer.finished_at ? String(offer.finished_at) : null,
      hotelId,
      matchStatus,
      groupName: group?.canonical_name || (offer.hotel_name ? String(offer.hotel_name) : undefined),
      groupConfidence: group?.confidence,
      groupWhy: group?.why,
      groupArea: group?.area,
      aspect: 0.62,
      drop: computeDrop(leak),
      evidence: Array.isArray(offer.evidence) ? (offer.evidence as EvidenceItem[]) : [],
      room_type: offer.room_type ? String(offer.room_type) : undefined,
      meal_plan: offer.meal_plan ? String(offer.meal_plan) : undefined,
      cancellation_policy: offer.cancellation_policy ? String(offer.cancellation_policy) : undefined,
      hotel_url: offer.hotel_url ? String(offer.hotel_url) : undefined,
      reconciliation: offer.reconciliation ? String(offer.reconciliation) : undefined,
      notes: offer.notes ? String(offer.notes) : undefined,
      mock: Boolean(offer.mock),
    };
  });
}
