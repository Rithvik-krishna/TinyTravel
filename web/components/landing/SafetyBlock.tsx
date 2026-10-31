import React from "react";

const ITEMS: Array<[string, string]> = [
  ["Use real details", "Agents type dummy guest details, never yours."],
  ["Go past payment", "Every run stops at the payment page. Nothing is booked."],
  ["Log in", "No accounts, no saved cards, no passwords."],
  ["Beat a captcha", "We don't solve captchas or enter OTPs. A blocked site is shown as blocked."],
];

export function SafetyBlock() {
  return (
    <section id="safety">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">What we never do</span>
          <h2>Guest checkout, stopped at the door.</h2>
        </div>
        <div className="safe">
          {ITEMS.map(([h, p]) => (
            <div key={h}>
              <h3>{h}</h3>
              <p>{p}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}