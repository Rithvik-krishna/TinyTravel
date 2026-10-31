"use client";

import React, { useEffect, useRef, useState } from "react";
import { TagItem } from "@/lib/tags";
import { inr, signedInr } from "@/lib/format";
import { EvidenceDialog, TrailRow } from "./EvidenceDialog";

const STEP_NAMES: Record<string, string> = {
  listing: "Listing",
  room: "Room selected",
  traveller_details: "Traveller details",
  payment: "Payment page",
};

function stepName(step: string): string {
  return STEP_NAMES[step] ?? step.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());
}

export function PriceTrail({ offer }: { offer: TagItem }) {
  const dlgRef = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const [sel, setSel] = useState<TrailRow | null>(null);

  const rows: TrailRow[] = offer.price_trail.map((p) => ({
    step: p.step,
    name: stepName(p.step),
    amount: p.amount,
    evidence: offer.evidence?.find((e) => e.step === p.step) ?? null,
  }));

  useEffect(() => {
    const d = dlgRef.current;
    if (sel && d && !d.open) d.showModal();
  }, [sel]);

  return (
    <div className="trail">
      <h3>Price trail</h3>
      <ol>
        {rows.map((r, i) => {
          const prev = i > 0 ? rows[i - 1].amount : null;
          const step = prev != null && r.amount !== prev ? r.amount - prev : null;
          return (
            <li key={r.step}>
              <span className="dot" />
              <div>
                <div className="name">{r.name}</div>
                <div className="sub">{r.evidence ? "Evidence captured" : "No evidence captured"}</div>
              </div>
              <div>
                <button
                  type="button"
                  className={`amt${r.evidence ? "" : " none"}`}
                  aria-label={`${r.name}, ${inr(r.amount)}. Show evidence`}
                  onClick={(e) => {
                    opener.current = e.currentTarget;
                    setSel(r);
                  }}
                >
                  {inr(r.amount)}
                </button>
                {step != null && <span className="d">{signedInr(step)}</span>}
              </div>
            </li>
          );
        })}
      </ol>
      <EvidenceDialog
        dialogRef={dlgRef}
        row={sel}
        sourceUrl={offer.hotel_url}
        onClosed={() => {
          setSel(null);
          opener.current?.focus();
        }}
      />
    </div>
  );
}