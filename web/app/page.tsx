import React from "react";
import Link from "next/link";
import KeyTagRail from "@/components/ui/key-tag-rail";
import ProvenanceBanner from "@/components/ProvenanceBanner";
import { getResults } from "@/lib/dataSource";
import { offersToTags } from "@/lib/tags";

export default async function Home() {
  const results = await getResults("demo");
  const tags = offersToTags(results);
  const isMock = Boolean(results?.mock ?? results?._meta?.mock ?? true);
  const savedLabel = results?._meta?.saved ? (results._meta.saved_label || "demo") : null;

  return (
    <div className="flex flex-col items-center justify-center py-2 sm:py-6 space-y-4">
      <div className="w-full flex justify-center">
        <ProvenanceBanner mock={isMock} savedLabel={savedLabel} />
      </div>

      <KeyTagRail
        items={tags}
        eyebrow="Verified before you pay"
        heading="The price you see isn't the price you pay."
        caption="Hotel key tags swing on touch, lift on hover, and flip to show the real payable price."
        action={
          <Link
            href="/search"
            className="inline-flex items-center justify-center rounded-full bg-brand px-7 py-3 text-sm font-semibold text-white shadow-md transition-all hover:opacity-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand active:scale-[0.98] motion-reduce:transition-none"
          >
            Verify prices
          </Link>
        }
      />
    </div>
  );
}
