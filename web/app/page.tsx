import React from "react";
import Link from "next/link";
import { getResults } from "@/lib/dataSource";
import { offersToTags, TagItem, ResultsData } from "@/lib/tags";
import { ProvenanceBanner } from "@/components/ProvenanceBanner";
import { KeyTagRail } from "@/components/ui/key-tag-rail";

// Section Components
import { NavBar } from "@/components/landing/NavBar";
import { ProofStrip } from "@/components/landing/ProofStrip";
import { TheProblem } from "@/components/landing/TheProblem";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { WatchItVerify } from "@/components/landing/WatchItVerify";
import { AllHotelsRail } from "@/components/landing/AllHotelsRail";
import { ProofNotPromises } from "@/components/landing/ProofNotPromises";
import { VerdictSection } from "@/components/landing/VerdictSection";
import { SafetyBlock } from "@/components/landing/SafetyBlock";
import { FAQ } from "@/components/landing/FAQ";
import { FinalCTA } from "@/components/landing/FinalCTA";
import { Footer } from "@/components/landing/Footer";

interface ExtendedResults extends ResultsData {
  mock?: boolean;
  _meta?: {
    mock?: boolean;
    saved?: boolean;
    saved_label?: string;
    saved_run_label?: string;
  };
  summary_strip?: {
    listings_found?: number;
    unique_hotels?: number;
    verified?: number;
    unverified?: number;
    blocked?: number;
    avg_fee_leak_pct?: number;
  };
  handoff?: {
    deep_link?: string;
  };
}

export default async function Home() {
  const results = (await getResults("demo")) as ExtendedResults | null;
  const allTags: TagItem[] = offersToTags(results);
  const heroTags = allTags.filter((t) => t.hotelId === "h1");

  const isMock = Boolean(results?.mock ?? results?._meta?.mock ?? true);
  const savedLabel = results?._meta?.saved
    ? results._meta.saved_label || "demo"
    : results?._meta?.saved_run_label || null;

  const deepLink = results?.handoff?.deep_link || "https://www.agoda.com/";

  // Extract La Marvella (h1) Cleartrip specific offer for "The Problem" and "Proof"
  const h1CleartripTag = allTags.find((t) => t.id === "h1_cleartrip");
  const listingPrice = h1CleartripTag?.listing ?? 8210;
  const payablePrice = h1CleartripTag?.payable ?? 11276;
  const feeLeakPct = h1CleartripTag?.fee_leak_pct ?? 37.3;

  return (
    <div className="w-full flex flex-col items-center bg-surface text-text overflow-x-hidden">
      {/* 1. Sticky Navigation Bar */}
      <NavBar isMock={isMock} />

      {/* Hero Centerpiece Section */}
      <section className="w-full min-h-[640px] lg:min-h-[85vh] lg:max-h-[880px] flex flex-col justify-center items-center py-6 sm:py-8">
        <div className="mb-4">
          <ProvenanceBanner mock={isMock} savedLabel={savedLabel} />
        </div>

        <KeyTagRail
          items={heroTags}
          eyebrow="Verified before you pay"
          heading="The price you see isn't the price you pay."
          caption="We probe travel sites down to the payment page to catch price inflation before you book."
          maxUnit={280}
          action={
            <div className="flex flex-wrap items-center justify-center gap-3 mt-1">
              <Link
                href="/search"
                className="inline-flex items-center justify-center rounded-full bg-brand px-7 py-3 text-sm font-semibold text-white shadow-md transition-all hover:opacity-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand active:scale-[0.98] motion-reduce:transition-none"
              >
                Verify prices
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center justify-center rounded-full border border-border bg-surface px-6 py-3 text-sm font-semibold text-text shadow-sm transition-all hover:bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand active:scale-[0.98] motion-reduce:transition-none"
              >
                See how it works
              </a>
            </div>
          }
        />
      </section>

      {/* 2. Proof Strip */}
      <ProofStrip summary={results?.summary_strip} isMock={isMock} />

      {/* 3. The Problem Section */}
      <TheProblem
        listingPrice={listingPrice}
        payablePrice={payablePrice}
        leakPct={feeLeakPct}
      />

      {/* 4. How It Works */}
      <HowItWorks />

      {/* 5. Watch It Verify (Simulation) */}
      <WatchItVerify />

      {/* 6. All Hotels 8-Tag Rail */}
      <AllHotelsRail
        items={allTags}
        hotelGroups={results?.hotel_groups}
      />

      {/* 7. Proof, Not Promises */}
      <ProofNotPromises
        hotelName={h1CleartripTag?.title || "La Marvella"}
        platform={h1CleartripTag?.platform || "Cleartrip"}
        priceTrail={h1CleartripTag?.price_trail}
        feeLines={h1CleartripTag?.fee_lines}
        finalPayable={payablePrice}
      />

      {/* 8. Verdict Section */}
      <VerdictSection deepLink={deepLink} />

      {/* 9. Safety & Privacy */}
      <SafetyBlock />

      {/* 10. Frequently Asked Questions */}
      <FAQ />

      {/* 11. Final Call To Action */}
      <FinalCTA />

      {/* 12. Footer */}
      <Footer />
    </div>
  );
}
