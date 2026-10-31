import React from "react";
import { UserX, ShieldCheck, CreditCard, Lock } from "lucide-react";

export function SafetyBlock() {
  const cards = [
    {
      icon: UserX,
      title: "Dummy details only",
      sub: "Test Guest, fake phone, disposable email",
      desc: "Our automated probes use disposable synthetic traveler records (Test Guest, 9000000000). Your actual identity is never entered into probe sessions.",
    },
    {
      icon: ShieldCheck,
      title: "Guest checkout only",
      sub: "We never create an account or log in as you",
      desc: "Probes navigate exclusively through anonymous guest checkout funnels. We do not link or access your personal travel booking accounts.",
    },
    {
      icon: CreditCard,
      title: "Stops at the payment page",
      sub: "We never enter card numbers or touch money",
      desc: "Automation stops strictly the millisecond the final payable balance is rendered. We never enter card details, CVVs, or process transactions.",
    },
    {
      icon: Lock,
      title: "Zero credentials stored",
      sub: "No passwords, no session tokens, no OTPs",
      desc: "We do not store passwords, bank OTPs, or active session tokens. When you decide to book, you pay directly on the official booking platform.",
    },
  ];

  return (
    <section id="safety" className="w-full py-16 sm:py-24 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto space-y-12">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Safety &amp; Privacy By Design
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            Strict safety invariants.
          </h2>
          <p className="text-sm sm:text-base text-text-muted">
            Engineered with zero-trust guardrails. We verify prices without compromising your security or privacy.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {cards.map((card, idx) => {
            const Icon = card.icon;
            return (
              <div
                key={idx}
                className="flex flex-col p-6 rounded-3xl bg-surface border border-border shadow-sm hover:border-brand/40 transition-colors space-y-3"
              >
                <div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-brand/10 text-brand mb-1">
                  <Icon className="w-6 h-6" />
                </div>

                <h3 className="text-base font-bold text-text leading-tight">
                  {card.title}
                </h3>

                <p className="text-xs font-semibold text-brand/90 leading-snug">
                  {card.sub}
                </p>

                <p className="text-xs text-text-muted leading-relaxed flex-1">
                  {card.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
