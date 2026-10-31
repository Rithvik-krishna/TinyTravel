"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Sparkles } from "lucide-react";

export function FinalCTA() {
  const router = useRouter();
  const [promptText, setPromptText] = useState(
    "Weekend in Bengaluru, 2 guests, under 10k/night"
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push("/search");
  };

  return (
    <section className="w-full py-20 sm:py-28 px-4 sm:px-6">
      <div className="max-w-4xl mx-auto rounded-3xl bg-surface border-2 border-brand/20 p-8 sm:p-14 text-center shadow-xl relative overflow-hidden">
        {/* Background ambient glow */}
        <div className="pointer-events-none absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-96 bg-brand/10 rounded-full blur-3xl" />

        <div className="relative z-10 space-y-6">
          <div className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 border border-brand/20 px-3 py-1 text-xs font-bold text-brand uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            Verified before you pay
          </div>

          <h2 className="text-3xl sm:text-5xl font-black tracking-tight text-text leading-tight max-w-2xl mx-auto">
            Stop guessing. See the price you&apos;ll actually pay.
          </h2>

          <p className="text-base sm:text-lg text-text-muted max-w-xl mx-auto">
            Our guest agents will audit the booking funnel down to checkout in real-time.
          </p>

          <form
            onSubmit={handleSubmit}
            className="flex flex-col sm:flex-row items-center gap-3 max-w-xl mx-auto pt-4"
          >
            <div className="relative w-full flex-1">
              <Search className="w-4 h-4 text-text-muted absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={promptText}
                onChange={(e) => setPromptText(e.target.value)}
                placeholder="Where are you travelling?"
                className="w-full rounded-full border border-border bg-surface-2 pl-11 pr-4 py-3.5 text-sm text-text placeholder-text-muted shadow-sm focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/30"
              />
            </div>
            <button
              type="submit"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-full bg-brand px-7 py-3.5 text-sm font-bold text-white shadow-md hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand active:scale-[0.98] transition-all whitespace-nowrap"
            >
              <span>Verify prices</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-text-muted pt-2">
            <span>✓ No login required</span>
            <span>✓ Zero payment data stored</span>
            <span>✓ 3 platforms checked concurrently</span>
          </div>
        </div>
      </div>
    </section>
  );
}
