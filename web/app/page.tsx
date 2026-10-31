import React from "react";
import Link from "next/link";
import { MOCK } from "@/lib/dataSource";
import { FlowShell } from "@/components/flow/FlowShell";
import { SearchForm } from "@/components/flow/SearchForm";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { SafetyBlock } from "@/components/landing/SafetyBlock";
import { Faq } from "@/components/landing/Faq";

export default function Home() {
  return (
    <FlowShell>
      <main id="top">
        <section className="search-hero" id="search">
          <div className="wrap">
            <div className="intro">
              <span className="eyebrow">Verified before you pay</span>
              <h1>
                The price you see isn&apos;t <em>the price you pay.</em>
              </h1>
              <p className="lede">
                Tell us where and when. Browser agents check out as a guest on Cleartrip, Agoda and Booking.com, follow the price to the payment
                page, and show you the proof.
              </p>
            </div>
            <SearchForm />
            {MOCK && (
              <p className="note">
                Just looking? <Link href="/investigation?id=mock_search" style={{ textDecoration: "underline" }}>Watch a sample run</Link>.
              </p>
            )}
          </div>
        </section>
        <HowItWorks />
        <SafetyBlock />
        <Faq />
      </main>
    </FlowShell>
  );
}
