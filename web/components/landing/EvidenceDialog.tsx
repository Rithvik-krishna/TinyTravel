"use client";

import React from "react";
import { EvidenceItem } from "@/lib/tags";
import { inr, longDateTime } from "@/lib/format";

export interface TrailRow {
  step: string;
  name: string;
  amount: number;
  evidence: EvidenceItem[];
}

interface Props {
  dialogRef: React.RefObject<HTMLDialogElement>;
  row: TrailRow | null;
  currency: string;
  sourceUrl?: string;
  /** Verbatim page text captured by the agent, by step. */
  pageText: Record<string, string | undefined>;
  onClosed: () => void;
}

const SHOW_PROVENANCE = process.env.NEXT_PUBLIC_SHOW_PROVENANCE === "1";

function Item({ ev, pageText }: { ev: EvidenceItem; pageText?: string }) {
  if (ev.type === "page_text") {
    return (
      <section style={{ display: "grid", gap: 8 }}>
        <h4 style={{ margin: 0, fontSize: 15 }}>Page text we captured</h4>
        {pageText ? (
          <pre className="ptext">{pageText}</pre>
        ) : (
          <p className="fine">The text for this step was not included in the results.</p>
        )}
      </section>
    );
  }
  if (ev.type === "recording") {
    return (
      <section style={{ display: "grid", gap: 8 }}>
        <h4 style={{ margin: 0, fontSize: 15 }}>Recording of the checkout</h4>
        {/^(https?:\/\/|\/)/.test(String(ev.url ?? "")) ? (
          <a className="btn sm ghost" href={ev.url} target="_blank" rel="noopener noreferrer" style={{ justifySelf: "start" }}>Open recording</a>
        ) : (
          <p className="fine">No recording link is available.</p>
        )}
        <p className="fine">Recording links can expire after a while.</p>
      </section>
    );
  }
  return (
    <section className="shot">
      {ev.url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={ev.url} alt={`Captured ${ev.type} at step ${ev.step}`} style={{ width: "100%", height: "100%", objectFit: "contain", borderRadius: 10 }} />
      ) : (
        "No image"
      )}
    </section>
  );
}

export function EvidenceDialog({ dialogRef, row, currency, sourceUrl, pageText, onClosed }: Props) {
  const first = row?.evidence[0];
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
              {row.name} · {inr(row.amount, currency)}
            </h3>
            {row.evidence.length > 0 ? (
              <>
                {row.evidence.map((ev, i) => (
                  <Item key={`${ev.type}-${i}`} ev={ev} pageText={pageText[ev.step]} />
                ))}
                <dl>
                  <dt>Step</dt>
                  <dd>{row.step}</dd>
                  {first && (
                    <>
                      <dt>Captured</dt>
                      <dd>{longDateTime(first.captured_at) || "N/A"}</dd>
                      <dt>Amount seen</dt>
                      <dd>{inr(first.extracted_value, first.currency || currency)}</dd>
                    </>
                  )}
                  {sourceUrl && (
                    <>
                      <dt>Source</dt>
                      <dd>{sourceUrl.replace(/^https?:\/\//, "")}</dd>
                    </>
                  )}
                </dl>
                {SHOW_PROVENANCE && row.evidence.some((e) => e.mock) && <span className="badge mock" style={{ justifySelf: "start" }}>Placeholder evidence</span>}
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