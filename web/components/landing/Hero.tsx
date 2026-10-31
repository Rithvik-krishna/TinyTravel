import React from "react";
import { TagItem } from "@/lib/tags";
import { LandingMeta } from "@/lib/landing";
import { KeyTagRail } from "./KeyTagRail";
import { Provenance } from "./Provenance";

interface HeroProps {
  tags: TagItem[];
  meta?: LandingMeta;
  checkIn?: string;
  checkOut?: string;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function stayDates(a?: string, b?: string): string {
  const pa = a?.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const pb = b?.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!pa || !pb) return "";
  const da = Number(pa[3]), db = Number(pb[3]);
  const ma = MONTHS[Number(pa[2]) - 1], mb = MONTHS[Number(pb[2]) - 1];
  if (!ma || !mb) return "";
  return ma === mb ? `${da}–${db} ${ma}` : `${da} ${ma}–${db} ${mb}`;
}

export function Hero({ tags, meta, checkIn, checkOut }: HeroProps) {
  const first = tags[0];
  const where = [first?.groupName ?? first?.title, first?.groupArea, stayDates(checkIn, checkOut)].filter(Boolean).join(", ");
  return (
    <section className="hero">
      <div className="wrap">
        <Provenance meta={meta} />
        <span className="eyebrow">Verified before you pay</span>
        <h1>
          The price you see isn&apos;t <em>the price you pay.</em>
        </h1>
        <p className="lede">
          TinyTravel sends browser agents through real hotel checkouts as a guest, follows the price to the payment page, and shows you the proof.
        </p>
        <div className="cta-row">
          <a className="btn" href="#verdict">Verify prices</a>
          <a className="btn ghost" href="#how">See how it works</a>
        </div>
        {tags.length > 0 && (
          <>
            <KeyTagRail tags={tags} width="clamp(190px, 20vw, 240px)" variant="hero" ariaLabel={`${first?.title ?? "Hotel"} offers on ${tags.length} sites`} />
            <p className="rail-note">
              {where ? `${where}. ` : ""}Touch a tag to swing it. Tap to flip it and see the price at the payment page.
            </p>
          </>
        )}
      </div>
    </section>
  );
}