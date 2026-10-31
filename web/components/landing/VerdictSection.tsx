"use client";

import React, { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { inr } from "@/lib/format";
import { Check, ShieldCheck, Sparkles, Smartphone, ExternalLink, Copy } from "lucide-react";

interface VerdictCard {
  badge: string;
  badgeColor: string;
  title: string;
  platform: string;
  payable: number;
  perks: string[];
  recommended?: boolean;
}

interface VerdictSectionProps {
  deepLink?: string;
}

export function VerdictSection({ deepLink = "https://www.agoda.com/" }: VerdictSectionProps) {
  const [copied, setCopied] = useState(false);

  const verdictCards: VerdictCard[] = [
    {
      badge: "Cheapest Verified",
      badgeColor: "bg-success/15 text-success border-success/30",
      title: "Lowest absolute verified rate",
      platform: "Agoda",
      payable: 10412,
      perks: [
        "Verified down to payment page",
        "Includes taxes & service fees",
        "Free cancellation included",
      ],
    },
    {
      badge: "Safe-Cheapest",
      badgeColor: "bg-brand/15 text-brand border-brand/30",
      title: "Zero-risk cancellation parity",
      platform: "Cleartrip",
      payable: 11276,
      perks: [
        "Free cancellation until 18 Nov 12:00",
        "Instant confirmation probe",
        "Clear domestic support line",
      ],
    },
    {
      badge: "Best for You",
      badgeColor: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30",
      title: "Optimal balance of price & safety",
      platform: "Agoda",
      payable: 10412,
      perks: [
        "Matches travel profile constraints",
        "Free breakfast & free WiFi",
        "Top customer sentiment score",
      ],
      recommended: true,
    },
  ];

  const handleCopyGuestDetails = () => {
    const text = "Name: Test Guest\nEmail: test.guest+probe@example.com\nPhone: 9000000000";
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="verdict" className="w-full py-16 sm:py-24 px-4 sm:px-6 bg-surface-2/40 border-t border-border">
      <div className="max-w-6xl mx-auto space-y-12">
        {/* Section Header */}
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Decision Intelligence
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            How TinyTravel helps you choose
          </h2>
          <p className="text-sm sm:text-base text-text-muted">
            We digest verified rates across funnels so you can book with confidence without paying hidden inflation.
          </p>
        </div>

        {/* Main Grid: 3 Verdict Cards (left) + Phone Mockup (right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left: 3 Verdict Cards (col-span-7) */}
          <div className="lg:col-span-7 space-y-4">
            {verdictCards.map((card, idx) => (
              <div
                key={idx}
                className={`p-6 rounded-3xl border transition-all ${
                  card.recommended
                    ? "bg-surface border-2 border-brand/50 shadow-md ring-1 ring-brand/20 relative"
                    : "bg-surface border border-border shadow-sm hover:border-brand/40"
                }`}
              >
                {card.recommended && (
                  <span className="absolute -top-3 right-6 rounded-full bg-brand px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white shadow-sm flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Recommended
                  </span>
                )}

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold border ${card.badgeColor}`}
                    >
                      {card.badge}
                    </span>
                    <span className="text-xs font-semibold text-text-muted">
                      via {card.platform}
                    </span>
                  </div>

                  <div className="text-left sm:text-right">
                    <span className="text-xs text-text-muted block">You pay</span>
                    <span className="text-2xl font-black text-danger tabular-nums">
                      {inr(card.payable)}
                    </span>
                  </div>
                </div>

                <h3 className="text-base font-bold text-text mb-2">{card.title}</h3>

                <ul className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-border/60">
                  {card.perks.map((perk, pIdx) => (
                    <li key={pIdx} className="flex items-center gap-1.5 text-xs text-text-muted">
                      <Check className="w-3.5 h-3.5 text-success flex-shrink-0" />
                      <span>{perk}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          {/* Right: Phone Mockup Handoff (col-span-5) */}
          <div className="lg:col-span-5 flex justify-center">
            <div className="w-full max-w-[340px] rounded-[44px] bg-slate-900 dark:bg-black p-3.5 border-4 border-slate-700/80 shadow-2xl">
              {/* Dynamic Island / Speaker cutout */}
              <div className="flex justify-center mb-3">
                <div className="w-24 h-4 bg-slate-800 rounded-full" />
              </div>

              {/* Screen Content */}
              <div className="rounded-[36px] bg-surface p-5 text-center space-y-4 border border-border">
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-brand">
                    Mobile Handoff
                  </span>
                  <h4 className="text-base font-bold text-text leading-tight">
                    Scan to continue on your phone
                  </h4>
                  <p className="text-xs text-text-muted">
                    We pass you straight to the real Agoda checkout.
                  </p>
                </div>

                {/* QR Code Container */}
                <div className="flex justify-center p-3 rounded-2xl bg-white border border-border/80 shadow-inner">
                  <QRCodeSVG
                    value={deepLink}
                    size={140}
                    level="M"
                    includeMargin={false}
                  />
                </div>

                <div className="space-y-2 pt-1 text-left bg-surface-2 p-3 rounded-2xl border border-border/70">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-text-muted">
                      Guest Probe Data
                    </span>
                    <button
                      type="button"
                      onClick={handleCopyGuestDetails}
                      className="text-[10px] font-bold text-brand hover:underline inline-flex items-center gap-1"
                    >
                      {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                      {copied ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <div className="text-[11px] font-mono text-text">
                    Test Guest • 9000000000
                  </div>
                </div>

                <div className="pt-1 flex items-center justify-center gap-1.5 text-[11px] font-medium text-text-muted">
                  <ShieldCheck className="w-4 h-4 text-success flex-shrink-0" />
                  <span>You pay on the real site. We never see your password.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
