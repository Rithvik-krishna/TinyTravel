import React from "react";
import { TagItem } from "@/lib/tags";
import { PriceTrail } from "./PriceTrail";
import { FeeBreakdown } from "./FeeBreakdown";

export function ProofSection({ offer }: { offer?: TagItem }) {
  return (
    <section id="proof">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">Proof, not promises</span>
          <h2>Every number links to its page.</h2>
          <p className="lede">
            {offer ? `${offer.title} on ${offer.platform}. ` : ""}Select an amount to see the evidence captured at that step.
          </p>
        </div>
        {offer ? (
          <div className="proof">
            <PriceTrail offer={offer} />
            <FeeBreakdown offer={offer} />
          </div>
        ) : (
          <p className="note">No offer to show a trail for.</p>
        )}
      </div>
    </section>
  );
}