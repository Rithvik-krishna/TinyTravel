import React from "react";
import Link from "next/link";
import { getResults, MOCK } from "@/lib/dataSource";
import { gapAmount, gapPct, inr, shortTime, signedInr } from "@/lib/format";
import { LandingResults } from "@/lib/landing";
import { offersToTags } from "@/lib/tags";
import { FlowShell } from "@/components/flow/FlowShell";
import { SearchForm } from "@/components/flow/SearchForm";

export const metadata = { title: "Book — TinyTravel" };

const Tick = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M5 12l4 4 10-10" />
  </svg>
);

export default async function Book() {
  // The "what you see / what you pay" example comes from the demo run, so it only exists in mock mode.
  let example: { listing: number; payable: number; platform: string; hotel: string; at: string } | null = null;
  if (MOCK) {
    const results: LandingResults = await getResults("demo");
    const heroId = results.verdicts?.hero_hotel_id;
    const t = offersToTags(results).find((x) => x.hotelId === heroId && x.status === "verified" && x.listing != null && x.payable != null);
    if (t && t.listing != null && t.payable != null) example = { listing: t.listing, payable: t.payable, platform: t.platform, hotel: t.title, at: shortTime(t.verifiedAt) };
  }
  const gap = example ? gapAmount(example.listing, example.payable) : null;
  const pct = example ? gapPct(example.listing, example.payable) : null;

  return (
    <FlowShell>
      <main className="wrap" id="top">
        <div className="bk-hero">
          <div>
            <span className="eyebrow">Book with proof</span>
            <h1 style={{ marginTop: 12 }}>
              Know what you&apos;ll <em>really pay</em> before you book.
            </h1>
            <p className="sub">
              We check Cleartrip, Agoda and Booking.com all the way to the payment page, as a guest, so the price you pick is the price you pay.
            </p>
            <ul className="ticks">
              <li><Tick /><span>Totals include taxes and fees, checked on the payment page</span></li>
              <li><Tick /><span>Free cancellation and non-refundable rooms are never mixed up</span></li>
              <li><Tick /><span>Nothing is booked. You finish on the real site</span></li>
            </ul>
          </div>
          <SearchForm />
        </div>

        {example && (
          <div className="example">
            <div className="box">
              <span className="muted" style={{ fontWeight: 600 }}>What you see</span>
              <span className="big">{inr(example.listing)}</span>
              <span className="muted">{example.hotel} on {example.platform}, listing price</span>
            </div>
            <div className="mid">
              <svg width="56" height="22" viewBox="0 0 56 22" fill="none" stroke="var(--warn)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M2 11h48M40 3l10 8-10 8" />
              </svg>
              {gap != null && pct != null && <b>{signedInr(gap)} ({pct > 0 ? "+" : ""}{pct}%)</b>}
              <span className="fine">observed on this run</span>
            </div>
            <div className="box">
              <span className="muted" style={{ fontWeight: 600 }}>What you pay</span>
              <span className="big" style={{ color: "var(--warn)" }}>{inr(example.payable)}</span>
              <span className="muted">Same room, at the payment page{example.at ? `, verified ${example.at}` : ""}. Example from demo data.</span>
            </div>
          </div>
        )}

        <div className="trio">
          <div><h3>We check like a buyer</h3><p>An agent picks the room and fills placeholder guest details on each site, then stops at the payment page.</p></div>
          <div><h3>You see the proof</h3><p>Every price links to the step where we saw it, with the time we checked.</p></div>
          <div><h3>You stay in control</h3><p>We never pay, log in, solve captchas or enter OTPs. You book on the real site.</p></div>
        </div>
        <p className="note" style={{ paddingBottom: 56 }}>
          New here? <Link href="/" style={{ textDecoration: "underline" }}>See how TinyTravel works</Link>.
        </p>
      </main>
    </FlowShell>
  );
}
