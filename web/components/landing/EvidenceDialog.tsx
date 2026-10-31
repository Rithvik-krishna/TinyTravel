"use client";

import React from "react";
import { EvidenceItem } from "@/lib/tags";
import { inr, longDateTime } from "@/lib/format";

export interface TrailRow {
  step: string;
  name: string;
  amount: number;
  evidence: EvidenceItem | null;
}

interface Props {
  dialogRef: React.RefObject<HTMLDialogElement>;
  row: TrailRow | null;
  sourceUrl?: string;
  onClosed: () => void;
}

export function EvidenceDialog({ dialogRef, row, sourceUrl, onClosed }: Props) {
  const ev = row?.evidence ?? null;
  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="ev-title"
      onClose={onClosed}
      onClick={(e) => {
        if (e.target === dialogRef.current) dialogRef.current?.close();
      }}
    >
      <div className="dlg">
        {row && (
          <>
            <h3 id="ev-title">
              {row.name} · {inr(row.amount)}
            </h3>
            {ev ? (
              <>
                <div className="shot">
                  {ev.url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={ev.url} alt={`Captured ${ev.type} at step ${ev.step}`} style={{ width: "100%", height: "100%", objectFit: "contain", borderRadius: 10 }} />
                  ) : (
                    "No image"
                  )}
                </div>
                <dl>
                  <dt>Step</dt>
                  <dd>{ev.step}</dd>
                  <dt>Captured</dt>
                  <dd>{longDateTime(ev.captured_at) || "N/A"}</dd>
                  <dt>Extracted</dt>
                  <dd>{inr(ev.extracted_value)} {ev.currency}</dd>
                  {sourceUrl && (
                    <>
                      <dt>Source</dt>
                      <dd>{sourceUrl.replace(/^https?:\/\//, "")}</dd>
                    </>
                  )}
                </dl>
                {ev.mock && (
                  <span className="badge mock" style={{ justifySelf: "start" }}>Mock evidence</span>
                )}
              </>
            ) : (
              <p style={{ color: "var(--muted)" }}>
                No evidence captured for this step. We never show a number as proven when there is no capture.
              </p>
            )}
          </>
        )}
        <button className="btn sm" type="button" onClick={() => dialogRef.current?.close()}>
          Close
        </button>
      </div>
    </dialog>
  );
}