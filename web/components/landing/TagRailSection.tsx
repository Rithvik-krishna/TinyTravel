import React from "react";
import { TagItem } from "@/lib/tags";
import { KeyTagRail } from "./KeyTagRail";

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

/** The three offers for the example hotel as hanging key tags. */
export function TagRailSection({ tags, checkIn, checkOut }: { tags: TagItem[]; checkIn?: string; checkOut?: string }) {
  if (tags.length === 0) return null;
  const first = tags[0];
  const where = [first.groupName ?? first.title, first.groupArea, stayDates(checkIn, checkOut)].filter(Boolean).join(", ");
  return (
    <section className="tag-section" aria-label="Offers for one hotel">
      <div className="wrap">
        <KeyTagRail tags={tags} width="clamp(190px, 20vw, 240px)" variant="hero" ariaLabel={`${first.title} offers on ${tags.length} sites`} />
        <p className="rail-note">{where ? `${where}. ` : ""}Hover over a tag (or tap it) to flip it and see the price at the payment page.</p>
      </div>
    </section>
  );
}