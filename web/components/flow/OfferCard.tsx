import React from "react";
import Link from "next/link";
import { TagItem, blockerLabel } from "@/lib/tags";
import { inr, shortTime } from "@/lib/format";
import { hotelHref, withId } from "@/lib/flow";

const CANCEL: Record<TagItem["cancellation_category"], string> = {
  free: "Free cancellation",
  partial: "Partial refund",
  non_refundable: "Non-refundable",
};

export function transparencyScore(t: TagItem): number | null {
  const s = (t.transparency as { score?: number | null } | null)?.score;
  return typeof s === "number" ? s : null;
}

interface Props {
  t: TagItem;
  searchId: string | null;
  /** Shared scale for the listing/payable bars within one hotel. */
  scaleMax: number;
  labels?: string[];
  notComparable?: boolean;
  showHotel?: boolean;
}

export function OfferCard({ t, searchId, scaleMax, labels = [], notComparable, showHotel }: Props) {
  const verified = t.status === "verified" && t.payable != null;
  const at = shortTime(t.verifiedAt);
  const score = transparencyScore(t);
  const pct = (n: number | null) => (n != null && scaleMax > 0 ? Math.max(4, Math.round((n / scaleMax) * 100)) : 0);
  return (
    <article className={`offer${verified ? "" : " na"}`} aria-label={`${t.title} on ${t.platform}`}>
      <div className="top">
        <b>{t.platform}</b>
        <span className={`badge ${t.status === "verified" ? "ok" : t.status === "blocked" ? "bad" : "warn"}`}>{t.status}</span>
      </div>
      {showHotel && <span className="why" style={{ fontWeight: 600, color: "var(--fg)" }}>{t.title}</span>}
      {labels.length > 0 && <div className="tags">{labels.map((l) => <span className="badge ok" key={l}>{l}</span>)}</div>}
      <div>
        <div className={`pay${verified ? "" : " none"}`}>{verified ? inr(t.payable, t.currency) : "N/A"}</div>
        {t.listing != null && <s>listing showed {inr(t.listing, t.currency)}</s>}
      </div>
      {verified && t.listing != null && (
        <div className="bars" aria-hidden="true">
          <i className="a" style={{ width: `${pct(t.listing)}%` }} />
          <i className="b" style={{ width: `${pct(t.payable)}%` }} />
        </div>
      )}
      {verified && t.fee_leak_pct != null && (
        <span className="badge" style={{ justifySelf: "start" }}>+{t.fee_leak_pct}% vs listing, observed on this run</span>
      )}
      {!verified && (
        <p className="why">
          {t.status === "blocked" ? `${blockerLabel(t.blocker)}. No payable price, no score.` : "Not verified: no payable price was captured, so there is no fee gap and no score."}
        </p>
      )}
      <div className="tags">
        {verified && <span className={`badge ${t.cancellation_category === "free" ? "ok" : "warn"}`}>{CANCEL[t.cancellation_category]}</span>}
        {notComparable && <span className="badge nc">Not comparable</span>}
      </div>
      <dl>
        {t.meal_plan && (<><dt>Meal plan</dt><dd>{t.meal_plan}</dd></>)}
        {t.room_type && (<><dt>Room</dt><dd>{t.room_type}</dd></>)}
        <dt>Transparency</dt><dd>{score == null ? "N/A" : `${score}/100`}</dd>
        {verified && at && (<><dt>Verified</dt><dd>{at}</dd></>)}
      </dl>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        {verified && <Link className="btn sm" href={hotelHref(t.hotelId, searchId, t.id)}>Book this</Link>}
        <Link className="proof" href={`${withId("/evidence", searchId)}${searchId ? "&" : "?"}offer=${encodeURIComponent(t.id)}`}>Show proof →</Link>
      </div>
    </article>
  );
}