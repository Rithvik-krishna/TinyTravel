import React from "react";
import Link from "next/link";

export function FinalCta() {
  return (
    <section className="final">
      <div className="wrap">
        <h2>Stop guessing. See the price you&apos;ll actually pay.</h2>
        <Link className="btn" href="/book">Book now</Link>
      </div>
    </section>
  );
}