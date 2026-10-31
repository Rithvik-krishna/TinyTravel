import React from "react";
import { Search, Bot, Scale, Receipt } from "lucide-react";

export function HowItWorks() {
  const steps = [
    {
      num: "01",
      icon: Search,
      title: "Tell us in one sentence",
      desc: "Natural language search. Type what you need—destination, guests, breakfast, cancellation rules—and our system extracts your exact constraints.",
      chip: "Natural language",
    },
    {
      num: "02",
      icon: Bot,
      title: "Guest probes",
      desc: "Our automated probes navigate travel sites as guest users with dummy details, moving through room selection and traveler entry to the payment page.",
      chip: "Payment page deep",
    },
    {
      num: "03",
      icon: Scale,
      title: "Fair offer matching",
      desc: "We verify room specifications, bed configurations, and cancellation policies for true apples-to-apples parity across platforms.",
      chip: "Policy parity",
    },
    {
      num: "04",
      icon: Receipt,
      title: "Verified link + proof",
      desc: "Review full fee breakdowns, DOM evidence, and a direct handoff link or mobile QR code to book directly on the real site.",
      chip: "Audited receipts",
    },
  ];

  return (
    <section id="how-it-works" className="w-full py-16 sm:py-24 px-4 sm:px-6 bg-surface-2/40 border-t border-border">
      <div className="max-w-6xl mx-auto">
        <div className="text-center max-w-2xl mx-auto mb-14 space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Process
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            How TinyTravel works
          </h2>
          <p className="text-base sm:text-lg text-text-muted">
            Four transparent steps from your plain-English prompt to an audited, uninflated booking.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="relative flex flex-col p-6 rounded-3xl bg-surface border border-border shadow-sm hover:border-brand/50 transition-all group"
              >
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-brand/10 text-brand group-hover:bg-brand group-hover:text-white transition-colors">
                    <Icon className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-bold uppercase tracking-wider text-text-muted">
                    {step.num}
                  </span>
                </div>

                <div className="inline-block mb-2">
                  <span className="text-[11px] font-semibold text-brand bg-brand/5 border border-brand/20 px-2 py-0.5 rounded-full">
                    {step.chip}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-text mb-2 tracking-tight">
                  {step.title}
                </h3>

                <p className="text-xs sm:text-sm text-text-muted leading-relaxed flex-1">
                  {step.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
