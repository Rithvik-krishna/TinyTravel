"use client";

import React from "react";
import { inr, longDateTime } from "@/lib/format";
import { useHistory } from "@/lib/extras";

/** Earlier observed prices for this hotel and site. Hidden when the history service is unavailable. */
export function PriceHistory({ hotel, platform }: { hotel: string; platform: string }) {
  const h = useHistory(hotel, platform.toLowerCase());
  if (h === null) return null;
  const points = [...h].reverse();
  const max = Math.max(1, ...points.map((p) => p.amount));
  const min = Math.min(...points.map((p) => p.amount));
  return (
    <div className="facts">
      <h2 style={{ fontSize: 20 }}>Observed prices from our runs</h2>
      {points.length < 2 ? (
        <p className="muted">No earlier observations yet. History builds up as more runs are saved, and we only show prices we actually saw.</p>
      ) : (
        <>
          <svg viewBox="0 0 300 70" role="img" aria-label="Observed prices over time" style={{ width: "100%", maxWidth: 480 }}>
            <polyline
              fill="none"
              stroke="var(--brass)"
              strokeWidth="2.5"
              points={points.map((p, i) => `${(i / (points.length - 1)) * 290 + 5},${65 - ((p.amount - min) / Math.max(1, max - min)) * 55}`).join(" ")}
            />
          </svg>
          <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 2, fontSize: 14 }}>
            {h.slice(0, 6).map((p, i) => (
              <li key={i}>{inr(p.amount, p.currency)} · {longDateTime(p.captured_at)}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}