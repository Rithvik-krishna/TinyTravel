import React from "react";

export function HowItWorks() {
  return (
    <section id="how">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">How it works</span>
          <h2>Four steps, no payment.</h2>
        </div>
        <div className="steps">
          <div className="step">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z" /></svg>
            <h3>Tell us in one sentence</h3>
            <p>&quot;Bengaluru, 20–21 Nov, 2 people, breakfast, free cancellation, under 12k.&quot;</p>
          </div>
          <div className="step">
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="4" width="18" height="14" rx="2" /><path d="M3 9h18M8 22h8" /></svg>
            <h3>Agents check out as a guest</h3>
            <p>One agent per site walks to the payment page with dummy details and stops.</p>
          </div>
          <div className="step">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="8" cy="12" r="5" /><circle cx="16" cy="12" r="5" /></svg>
            <h3>We match the same hotel</h3>
            <p>Listings are grouped across sites and only fair offers are compared.</p>
          </div>
          <div className="step">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12l4 4 10-10" /></svg>
            <h3>You get proof and a link</h3>
            <p>A verified price with evidence, and a link to pay on the real site.</p>
          </div>
        </div>
      </div>
    </section>
  );
}