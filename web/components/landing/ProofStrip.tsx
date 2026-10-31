import React from "react";
import { SummaryStrip } from "@/lib/landing";

interface ProofStripProps {
  summary?: SummaryStrip;
  sites: number;
}

function cell(n: string, l: string) {
  return (
    <div className="cell">
      <span className="n">{n}</span>
      <span className="l">{l}</span>
    </div>
  );
}

const num = (n: number | null | undefined) => (n == null ? "N/A" : String(n));

export function ProofStrip({ summary, sites }: ProofStripProps) {
  const leak = summary?.avg_fee_leak_pct;
  return (
    <section className="strip" aria-label="Run summary">
      <div className="wrap">
        {cell(sites > 0 ? String(sites) : "N/A", "sites checked as a guest")}
        {cell(num(summary?.unique_hotels), "hotels compared")}
        {cell(num(summary?.verified), "prices verified at the payment page")}
        {cell(leak == null ? "N/A" : `${leak}%`, "average gap, listing to payable (observed on this run)")}
      </div>
    </section>
  );
}