import React from "react";
import Link from "next/link";
import { TagItem } from "@/lib/tags";
import { LandingMeta } from "@/lib/landing";
import { gapAmount, gapPct, inr, signedInr } from "@/lib/format";
import { Provenance } from "./Provenance";

interface HeroProps {
  /** The offer shown in the example card (the demo run's hero offer). */
  offer?: TagItem;
  meta?: LandingMeta;
}

const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d={d} />
  </svg>
);

const TRUST: Array<[string, string]> = [
  ["Agents check as a guest", "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 3.6-7 8-7s8 3 8 7"],
  ["Payment page reached, never paid", "M3 6h18v12H3zM3 10h18"],
  ["Proof for every price", "M5 12l4 4 10-10"],
  ["Same hotel grouped across sites", "M9 12a5 5 0 105 0M15 12a5 5 0 10-5 0"],
  ["You finish on the real site", "M7 17L17 7M9 7h8v8"],
];

export function Hero({ offer, meta }: HeroProps) {
  const gap = gapAmount(offer?.listing, offer?.payable);
  const pct = gapPct(offer?.listing, offer?.payable);
  return (
    <section className="hero2">
      <div className="wrap" style={{ display: "grid", gridTemplateRows: "1fr auto", minHeight: "inherit" }}>
        <div className="hero-main">
          <div className="hero-copy">
            <Provenance meta={meta} />
            <h1>The price you see isn&apos;t the price you pay.</h1>
            <p className="lede">
              TinyTravel sends browser agents through real hotel checkouts as a guest, follows the price to the payment page, and shows you the proof.
            </p>
            <div className="cta-row">
              <Link className="btn" href="/book">Book now</Link>
              <a className="textlink" href="#how">See how it works ↗</a>
            </div>
          </div>
          {offer && offer.listing != null && offer.payable != null && (
            <aside className="hero-card glasscard" aria-label="Example from a recorded run">
              <span className="head">{offer.groupName ?? offer.title} · {offer.platform}</span>
              <div className="row"><span>Listed</span><b>{inr(offer.listing, offer.currency)}</b></div>
              <div className="row"><span>At payment</span><b>{inr(offer.payable, offer.currency)}</b></div>
              {gap != null && pct != null && (
                <span className="pill" style={{ justifySelf: "start" }}>{signedInr(gap, offer.currency)} · {pct > 0 ? "+" : ""}{pct}%</span>
              )}
              <span className="foot">Example from demo data · observed on this run</span>
            </aside>
          )}
        </div>
        <ul className="trust">
          {TRUST.map(([label, d]) => (
            <li key={label}>
              <Icon d={d} />
              <span>{label}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}