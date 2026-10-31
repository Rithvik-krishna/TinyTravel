import React from "react";
import { ChevronDown, HelpCircle } from "lucide-react";

export function FAQ() {
  const faqs = [
    {
      q: "How do you make money?",
      a: "TinyTravel is currently a zero-margin public beta. In production, we earn standard affiliate referral commissions when you click out to finalize your booking directly on the platform. We never accept sponsorships to promote dishonest rates or falsify rankings.",
    },
    {
      q: "Can you book for me?",
      a: "No. TinyTravel is strictly a price verification and audit engine. We do not process payments, store credit card details, or act as an intermediary travel agent. When you pick a deal, we hand you directly over to the official platform via deep-link or mobile QR code to book in your own name.",
    },
    {
      q: "Why are prices different between the listing and payment page?",
      a: "Online travel agencies use different models: some omit mandatory local hotel taxes on listing cards, others append late convenience fees during checkout, and prices may shift dynamically based on session timing. We only report observed numbers across the funnel.",
    },
    {
      q: "What happens when a site blocks you?",
      a: "We show 'Blocked' honestly. If a platform presents an anti-bot challenge (captcha), OTP requirement, or session timeout, our agents stop immediately and mark the offer as Blocked with price 'N/A'. We never fabricate numbers or guess unverified totals.",
    },
  ];

  return (
    <section id="faq" className="w-full py-16 sm:py-24 px-4 sm:px-6 bg-surface-2/40 border-t border-border">
      <div className="max-w-3xl mx-auto space-y-10">
        <div className="text-center space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Frequently Asked Questions
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            Transparent answers.
          </h2>
          <p className="text-sm sm:text-base text-text-muted">
            Everything you need to know about how TinyTravel probes, reconciles, and reports hotel pricing.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, idx) => (
            <details
              key={idx}
              className="group p-5 rounded-2xl bg-surface border border-border shadow-sm transition-colors open:border-brand/40"
            >
              <summary className="flex items-center justify-between cursor-pointer list-none font-bold text-base text-text group-hover:text-brand transition-colors focus-visible:outline-none">
                <span>{faq.q}</span>
                <ChevronDown className="w-5 h-5 text-text-muted transition-transform duration-200 group-open:rotate-180 flex-shrink-0 ml-3" />
              </summary>
              <p className="mt-3 text-xs sm:text-sm text-text-muted leading-relaxed border-t border-border/60 pt-3">
                {faq.a}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
