import React from "react";
import Link from "next/link";
import KeyTagRail from "@/components/ui/key-tag-rail";
import ProvenanceBanner from "@/components/ProvenanceBanner";
import { getResults } from "@/lib/dataSource";
import { offersToTags } from "@/lib/tags";

export default async function Home() {
  const results = await getResults("demo");
  const allTags = offersToTags(results);
  const heroTags = allTags.filter((t) => t.hotelId === "h1");
  const isMock = Boolean(results?.mock ?? results?._meta?.mock ?? true);
  const savedLabel = results?._meta?.saved ? (results._meta.saved_label || "demo") : null;

  return (
    <div className="w-full flex flex-col items-center">
      {/* Hero Section */}
      <section className="w-full min-h-[88vh] flex flex-col justify-center items-center py-6 sm:py-10">
        <div className="mb-4">
          <ProvenanceBanner mock={isMock} savedLabel={savedLabel} />
        </div>

        <KeyTagRail
          items={heroTags}
          eyebrow="Verified before you pay"
          heading="The price you see isn't the price you pay."
          caption="We probe travel sites down to the payment page to catch price inflation before you book."
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
    </div>
  );
}
