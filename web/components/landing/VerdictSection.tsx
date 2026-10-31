import React from "react";
import Link from "next/link";
import { hotelHref } from "@/lib/flow";
import { TagItem } from "@/lib/tags";
import { inr } from "@/lib/format";
import { Handoff, NonComparableWarning, VerdictPick } from "@/lib/landing";
import { HandoffPhone } from "./HandoffPhone";
import { RecheckButton } from "./RecheckButton";

interface Props {
  hotelName?: string;
  tags: TagItem[];
  pick?: VerdictPick;
  warnings: NonComparableWarning[];
  handoff?: Handoff | null;
  /** When set (flow pages), cards link to the hotel page for that search. */
  searchId?: string | null;
  /** Landing page: leave the "verified at <time>" out of the handoff note. */
  hideVerifiedTime?: boolean;
}

const LABELS: Array<[keyof VerdictPick, string]> = [
  ["cheapest_verified", "Cheapest verified"],
  ["safe_cheapest", "Safe-cheapest"],
  ["best_for_you", "Best for you"],
];

export function VerdictSection({ hotelName, tags, pick, warnings, handoff, searchId, hideVerifiedTime }: Props) {
  // One card per offer; verdicts that point at the same offer share a card.
  const cards = new Map<string, string[]>();
  for (const [key, label] of LABELS) {
    const id = pick?.[key];
    if (!id) continue;
    cards.set(id, [...(cards.get(id) ?? []), label]);
  }
  const merged = Array.from(cards.values()).some((l) => l.length > 1);
  const platform = handoff?.platform ?? "the site";

  return (
    <section id="verdict">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">Your verdict</span>
          <h2>Pick, then pay on the real site.</h2>
          <p className="lede">{hotelName ? `${hotelName}: the picks below come from prices we verified at the payment page.` : "The picks below come from prices we verified at the payment page."}</p>
        </div>
        <div className="verdict">
          {Array.from(cards.entries()).map(([id, labels]) => {
            const t = tags.find((x) => x.id === id);
            if (!t) return null;
            const best = labels.includes("Best for you") || labels.includes("Safe-cheapest");
            const warn = warnings.find((w) => w.offer_id === id);
            const nonRefundable = t.cancellation_category === "non_refundable";
            return (
              <div className={`vcard${best ? " best" : ""}`} key={id}>
                <span className={`badge${best ? " ok" : ""}`}>{labels.join(" · ")}</span>
                <h3>{t.platform}</h3>
                <span className="big">{inr(t.payable, t.currency)}</span>
                {t.listing != null && <s>listing showed {inr(t.listing, t.currency)}</s>}
                <div className="tags">
                  {nonRefundable && <span className="badge warn">Non-refundable</span>}
                  {warn && <span className="badge nc">Not comparable</span>}
                  {t.cancellation_category === "free" && t.cancellation_policy && <span className="badge ok">{t.cancellation_policy}</span>}
                </div>
                {warn?.message && <p style={{ color: "var(--muted)", fontSize: 14 }}>{warn.message}</p>}
                {labels.length > 1 && merged && (
                  <p style={{ color: "var(--muted)", fontSize: 14 }}>These picks are the same offer, so they share one card.</p>
                )}
                {searchId !== undefined && t.status === "verified" && (
                  <Link className={`btn sm${best ? " pink" : ""}`} href={hotelHref(t.hotelId, searchId, t.id)} style={{ justifySelf: "start" }}>View hotel and book</Link>
                )}
                {handoff?.offer_id === id && <RecheckButton offerId={id} platform={platform} />}
              </div>
            );
          })}
          <HandoffPhone handoff={handoff} hideVerifiedTime={hideVerifiedTime} />
        </div>
        {handoff && <p className="note">The link opens the property on {platform}. Pick exactly this room; the price should match.</p>}
      </div>
    </section>
  );
}