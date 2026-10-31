import React from "react";

const QA: Array<[string, string]> = [
  ["Is it free?", "The demo is free to try. Each full investigation uses real agent time, so a live run costs a few dollars to operate."],
  ["Do you book for me?", "No. We hand you a link and a QR code. You pay on the real site."],
  ["Why might prices differ from the listing?", "We report what we observed on this run. We don't claim why it changed."],
  ["What if a site blocks us?", "It is shown as blocked or unverified, with the reason. It never gets a score and never a made-up price."],
];

export function Faq() {
  return (
    <section id="faq">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">Questions</span>
          <h2>Plain answers.</h2>
        </div>
        <div className="faq">
          {QA.map(([q, a]) => (
            <details key={q}>
              <summary>{q}</summary>
              <p>{a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}