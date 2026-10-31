import React from "react";
import { TagItem, } from "@/lib/tags";
import { gapAmount, gapPct, inr, shortTime, signedInr } from "@/lib/format";
import { cancellationText } from "@/lib/landing";

export function GapSection({ offer }: { offer?: TagItem }) {
  const gap = gapAmount(offer?.listing, offer?.payable);
  const pct = gapPct(offer?.listing, offer?.payable);
  const verified = offer?.status === "verified" && offer.payable != null;
  const at = shortTime(offer?.verifiedAt);
  const desc = offer
    ? [offer.title, offer.room_type, offer.meal_plan?.toLowerCase(), cancellationText(offer.cancellation_category)].filter(Boolean).join(", ") + "."
    : "";
  return (
    <section id="problem">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">The gap</span>
          <h2>Same room, two numbers.</h2>
          <p className="lede">We follow the price from the listing to the payment page and report what we observed on this run.</p>
        </div>
        <div className="gap-grid">
          <div className="panel">
            <span className="lab mono" style={{ color: "var(--muted)" }}>What you see · {offer?.platform ?? "Listing"} listing</span>
            <span className="big">{inr(offer?.listing)}</span>
            <p style={{ color: "var(--muted)" }}>{desc}</p>
          </div>
          <div className="arrow">
            <svg viewBox="0 0 70 26" fill="none" stroke="var(--brass-hi)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M2 13h62M52 4l12 9-12 9" />
            </svg>
            {gap != null && pct != null ? (
              <>
                <span className="pill">{signedInr(gap)} · {pct > 0 ? "+" : ""}{pct}%</span>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>observed on this run</span>
              </>
            ) : (
              <span className="pill">N/A</span>
            )}
          </div>
          <div className="panel pay">
            <span className="lab mono" style={{ color: "var(--brass-hi)" }}>What you pay · {offer?.platform ?? "Payment"} payment page</span>
            <span className="big">{verified ? inr(offer?.payable) : "N/A"}</span>
            <p style={{ color: "var(--muted)" }}>
              {verified ? `Verified${at ? ` at ${at}` : ""}. The trail is in the proof section below.` : "No payable price was verified for this offer."}
            </p>
          </div>
        </div>
        <p className="note">We report the numbers. We do not claim why a price moved.</p>
      </div>
    </section>
  );
}