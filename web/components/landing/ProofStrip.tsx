import React from "react";
import MockBadge from "@/components/MockBadge";

interface SummaryStripData {
  listings_found?: number;
  unique_hotels?: number;
  verified?: number;
  unverified?: number;
  blocked?: number;
  avg_fee_leak_pct?: number;
}

interface ProofStripProps {
  summary?: SummaryStripData;
  isMock?: boolean;
}

export function ProofStrip({ summary, isMock = true }: ProofStripProps) {
  const sitesChecked = 3;
  const hotelsCount = summary?.unique_hotels ?? 3;
  const verifiedCount = summary?.verified ?? 6;
  const avgLeak = summary?.avg_fee_leak_pct ?? 19.4;

  const stats = [
    {
      label: "Sites checked",
      value: `${sitesChecked}`,
      detail: "Agoda, Booking, Cleartrip",
    },
    {
      label: "Hotels compared",
      value: `${hotelsCount}`,
      detail: "Normalized rooms & dates",
    },
    {
      label: "Prices verified",
      value: `${verifiedCount}`,
      detail: "Reached payment page",
    },
    {
      label: "Average price gap",
      value: `+${avgLeak}%`,
      detail: "observed on this run",
      highlight: true,
    },
  ];

  return (
    <section className="w-full border-y border-border bg-surface-2/60 py-8 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-success animate-pulse" />
            <h2 className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-text-muted">
              Live Probe Summary
            </h2>
          </div>
          {isMock && (
            <div className="flex items-center">
              <MockBadge show />
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
          {stats.map((stat, idx) => (
            <div
              key={idx}
              className="flex flex-col p-4 sm:p-5 rounded-2xl bg-surface border border-border shadow-sm hover:border-brand/40 transition-colors"
            >
              <span className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-1">
                {stat.label}
              </span>
              <span
                className={`text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight tabular-nums mb-1 ${
                  stat.highlight ? "text-danger" : "text-text"
                }`}
              >
                {stat.value}
              </span>
              <span className="text-[11px] sm:text-xs text-text-muted">
                {stat.detail}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
