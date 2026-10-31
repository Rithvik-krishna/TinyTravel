import React from "react";
import { ArrowRight, ArrowDown } from "lucide-react";
import { inr } from "@/lib/format";

interface TheProblemProps {
  listingPrice?: number;
  payablePrice?: number;
  leakPct?: number;
}

export function TheProblem({
  listingPrice = 8210,
  payablePrice = 11276,
  leakPct = 37.3,
}: TheProblemProps) {
  const diff = payablePrice - listingPrice;

  return (
    <section className="w-full py-16 sm:py-24 px-4 sm:px-6">
      <div className="max-w-5xl mx-auto text-center">
        {/* Section Header */}
        <div className="space-y-3 mb-12">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            The Reality of Travel Booking
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            The price you see isn&apos;t the price you pay.
          </h2>
          <p className="max-w-2xl mx-auto text-base sm:text-lg text-text-muted">
            We follow the price from the listing to the payment page.
          </p>
        </div>

        {/* Comparison Cards & Central Bridge */}
        <div className="relative flex flex-col md:flex-row items-center justify-center gap-6 lg:gap-8">
          {/* Card Left: What you see */}
          <div className="w-full md:w-1/2 p-6 sm:p-8 rounded-3xl bg-surface border border-border shadow-sm text-left space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                What you see
              </span>
              <span className="rounded-full bg-surface-2 border border-border px-3 py-1 text-xs font-medium text-text-muted">
                Search results
              </span>
            </div>

            <div>
              <div className="text-sm font-semibold text-brand">Cleartrip</div>
              <div className="text-xl sm:text-2xl font-bold text-text">La Marvella</div>
              <div className="text-xs text-text-muted mt-0.5">Deluxe Double • 2 guests • 1 night</div>
            </div>

            <div className="pt-2 border-t border-border/80">
              <span className="text-xs text-text-muted block mb-1">Observed listing price</span>
              <div className="text-3xl sm:text-4xl font-extrabold text-text tabular-nums">
                {inr(listingPrice)}
              </div>
            </div>

            <div className="text-xs text-text-muted italic">
              Headline rate shown on search results card.
            </div>
          </div>

          {/* Central Arrow & Delta Chip */}
          <div className="flex flex-col items-center justify-center z-10 -my-2 md:my-0">
            <div className="rounded-full bg-danger/10 border border-danger/30 text-danger px-3.5 py-1.5 text-xs font-bold whitespace-nowrap shadow-sm mb-2">
              +{leakPct}% observed on this run
            </div>
            <div className="hidden md:flex items-center justify-center w-10 h-10 rounded-full bg-surface-2 border border-border shadow-sm text-danger">
              <ArrowRight className="w-5 h-5" />
            </div>
            <div className="md:hidden flex items-center justify-center w-10 h-10 rounded-full bg-surface-2 border border-border shadow-sm text-danger">
              <ArrowDown className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-semibold text-text-muted mt-1 tabular-nums">
              +{inr(diff)} gap
            </div>
          </div>

          {/* Card Right: What you pay */}
          <div className="w-full md:w-1/2 p-6 sm:p-8 rounded-3xl bg-surface border-2 border-danger/30 shadow-md text-left space-y-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-danger/5 rounded-full blur-2xl -mr-6 -mt-6 pointer-events-none" />

            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-danger">
                What you pay
              </span>
              <span className="rounded-full bg-danger/10 border border-danger/20 px-3 py-1 text-xs font-semibold text-danger">
                Payment screen
              </span>
            </div>

            <div>
              <div className="text-sm font-semibold text-brand">Cleartrip</div>
              <div className="text-xl sm:text-2xl font-bold text-text">La Marvella</div>
              <div className="text-xs text-text-muted mt-0.5">Final amount due at checkout</div>
            </div>

            <div className="pt-2 border-t border-border/80">
              <span className="text-xs text-danger font-semibold block mb-1">Observed payable price</span>
              <div className="text-3xl sm:text-4xl font-extrabold text-danger tabular-nums">
                {inr(payablePrice)}
              </div>
            </div>

            <div className="text-xs text-text-muted">
              Includes base fare, taxes &amp; convenience fees reached at step 4.
            </div>
          </div>
        </div>

        {/* Section Caption */}
        <p className="mt-8 text-xs sm:text-sm text-text-muted max-w-xl mx-auto">
          We follow the price from the listing to the payment page. Never guessing, never assuming cause.
        </p>
      </div>
    </section>
  );
}
