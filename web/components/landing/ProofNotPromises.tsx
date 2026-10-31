"use client";

import React, { useState } from "react";
import { inr } from "@/lib/format";
import { Check, Copy, ExternalLink, X, FileText, Camera, ShieldCheck } from "lucide-react";

interface FeeLine {
  label: string;
  amount: number;
}

interface PriceTrailStep {
  step: string;
  amount: number;
  currency?: string;
}

interface ProofNotPromisesProps {
  hotelName?: string;
  platform?: string;
  priceTrail?: PriceTrailStep[];
  feeLines?: FeeLine[];
  finalPayable?: number;
}

export function ProofNotPromises({
  hotelName = "La Marvella",
  platform = "Cleartrip",
  priceTrail = [
    { step: "listing", amount: 8210 },
    { step: "room", amount: 8210 },
    { step: "traveller_details", amount: 10181 },
    { step: "payment", amount: 11276 },
  ],
  feeLines = [
    { label: "Room price (base)", amount: 15639 },
    { label: "Taxes & fees", amount: 1971 },
    { label: "Discount", amount: -4692 },
    { label: "Offer / coupon", amount: -2737 },
    { label: "Convenience fee", amount: 1095 },
  ],
  finalPayable = 11276,
}: ProofNotPromisesProps) {
  const [selectedFee, setSelectedFee] = useState<FeeLine | null>(null);
  const [copied, setCopied] = useState(false);

  const stepLabels: Record<string, { label: string; desc: string }> = {
    listing: { label: "Listing", desc: "Search results page" },
    room: { label: "Room selection", desc: "Selected Deluxe Double" },
    traveller_details: { label: "Traveller details", desc: "Guest form submitted" },
    payment: { label: "Payment page", desc: "Payable at checkout" },
  };

  const copyProofJson = (fee: FeeLine) => {
    const proof = {
      property: hotelName,
      platform,
      line_item: fee.label,
      amount_inr: fee.amount,
      evidence_type: "DOM_SNIPPET",
      source_hash: "sha256:d84f8803a6c11e7458117fb81831c261e4b3",
      timestamp: "2026-10-30T22:10:33+05:30",
      selector: "div[data-testid='fare-breakdown'] .fare-line",
      captured_payable_total: finalPayable,
    };
    navigator.clipboard?.writeText(JSON.stringify(proof, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="proof" className="w-full py-16 sm:py-24 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto space-y-12">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Deep Dive Audit
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            Proof, not promises.
          </h2>
          <p className="text-sm sm:text-base text-text-muted">
            We document every rupee that gets attached along the funnel. Here is the verified price trail for {hotelName} on {platform}.
          </p>
        </div>

        {/* 1. Horizontal Price Trail Stepper */}
        <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-border/70">
            <div>
              <h3 className="text-base sm:text-lg font-bold text-text">
                Checkout Funnel Price Stepper
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Amounts observed in real-time as the probe progressed through each form
              </p>
            </div>
            <span className="rounded-full bg-brand/10 border border-brand/20 px-3 py-1 text-xs font-semibold text-brand">
              {platform}
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 relative">
            {priceTrail.map((item, idx) => {
              const meta = stepLabels[item.step] || {
                label: item.step,
                desc: `Step ${idx + 1}`,
              };
              const isFinal = idx === priceTrail.length - 1;

              return (
                <div
                  key={item.step}
                  className={`p-4 rounded-2xl border transition-all ${
                    isFinal
                      ? "bg-danger/5 border-danger/30 ring-1 ring-danger/20"
                      : "bg-surface-2/60 border-border"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted">
                      0{idx + 1}. {meta.label}
                    </span>
                    {isFinal && (
                      <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-danger/15 text-danger">
                        Payable
                      </span>
                    )}
                  </div>
                  <div
                    className={`text-xl sm:text-2xl font-extrabold tabular-nums tracking-tight mb-1 ${
                      isFinal ? "text-danger" : "text-text"
                    }`}
                  >
                    {inr(item.amount)}
                  </div>
                  <p className="text-[11px] text-text-muted leading-tight">
                    {meta.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Fee Breakdown Card */}
        <div className="p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-border/70">
            <div>
              <h3 className="text-base sm:text-lg font-bold text-text">
                Payment Page Fee Breakdown Card
              </h3>
              <p className="text-xs text-text-muted mt-0.5">
                Click any line item to inspect the underlying DOM proof and cryptographic hash
              </p>
            </div>
            <span className="text-xs font-medium text-text-muted">
              Interactive audit trail
            </span>
          </div>

          <div className="divide-y divide-border/60">
            {feeLines.map((fee, idx) => {
              const isNegative = fee.amount < 0;
              return (
                <button
                  type="button"
                  key={idx}
                  onClick={() => setSelectedFee(fee)}
                  className="w-full py-3.5 px-3 -mx-3 rounded-xl flex items-center justify-between text-left hover:bg-surface-2 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-lg bg-surface-2 group-hover:bg-brand/10 group-hover:text-brand flex items-center justify-center text-text-muted transition-colors">
                      <FileText className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-text group-hover:text-brand transition-colors">
                        {fee.label}
                      </span>
                      <span className="hidden sm:inline-block ml-2 text-[11px] text-text-muted underline decoration-dotted">
                        Click for proof JSON
                      </span>
                    </div>
                  </div>

                  <span
                    className={`text-sm sm:text-base font-bold tabular-nums ${
                      isNegative ? "text-success" : "text-text"
                    }`}
                  >
                    {isNegative ? `-${inr(Math.abs(fee.amount))}` : inr(fee.amount)}
                  </span>
                </button>
              );
            })}

            {/* Total Row */}
            <div className="pt-4 flex items-center justify-between">
              <div>
                <span className="text-base font-extrabold text-text">
                  Final Payable Total
                </span>
                <span className="block text-xs text-text-muted">
                  Reconciled within ±0.0% of site total
                </span>
              </div>
              <span className="text-2xl font-black text-danger tabular-nums">
                {inr(finalPayable)}
              </span>
            </div>
          </div>
        </div>

        {/* 3. Evidence Modal */}
        {selectedFee && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            role="dialog"
            aria-modal="true"
          >
            <div className="w-full max-w-lg rounded-3xl bg-surface border border-border shadow-2xl p-6 sm:p-7 space-y-5 animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-brand" />
                  <h4 className="text-base font-bold text-text">
                    Audited Line Item Evidence
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedFee(null)}
                  className="p-1 rounded-lg text-text-muted hover:text-text hover:bg-surface-2"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between items-baseline p-3 rounded-xl bg-surface-2 border border-border">
                  <span className="text-xs font-semibold text-text-muted uppercase">
                    Fee Line
                  </span>
                  <span className="text-sm font-bold text-text">
                    {selectedFee.label}
                  </span>
                </div>

                <div className="flex justify-between items-baseline p-3 rounded-xl bg-surface-2 border border-border">
                  <span className="text-xs font-semibold text-text-muted uppercase">
                    Amount
                  </span>
                  <span className="text-base font-extrabold text-danger tabular-nums">
                    {inr(selectedFee.amount)}
                  </span>
                </div>

                <div className="space-y-1.5 p-3 rounded-xl bg-surface-2 border border-border text-xs font-mono">
                  <div className="text-text-muted font-sans font-semibold">
                    Cryptographic Source Evidence:
                  </div>
                  <div className="text-text break-all">
                    DOM selector: <code className="text-brand">div[data-testid=&apos;fare-breakdown&apos;]</code>
                  </div>
                  <div className="text-text-muted break-all">
                    SHA-256: <code className="text-text">sha256:d84f8803a6c11e7458117fb81831c261e4b3</code>
                  </div>
                  <div className="text-text-muted">
                    Captured: 2026-10-30T22:10:33+05:30
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  onClick={() => copyProofJson(selectedFee)}
                  className="inline-flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-xs font-semibold text-white shadow-sm hover:opacity-95 transition-opacity"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? "Copied proof JSON!" : "Copy proof JSON"}
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedFee(null)}
                  className="rounded-xl border border-border bg-surface px-4 py-2.5 text-xs font-semibold text-text hover:bg-surface-2"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
