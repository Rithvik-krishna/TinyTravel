import React from "react";
import script from "@fixtures/sse_script.json";
import "./landing.css";
import { getHandoff, getResults } from "@/lib/dataSource";
import { offersToTags } from "@/lib/tags";
import { Handoff, LandingResults } from "@/lib/landing";
import type { StreamEvent } from "@/lib/useInvestigationStream";

import { NavBar } from "@/components/landing/NavBar";
import { Hero } from "@/components/landing/Hero";
import { ProofStrip } from "@/components/landing/ProofStrip";
import { GapSection } from "@/components/landing/GapSection";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { LiveReplay } from "@/components/landing/LiveReplay";
import { HotelGroups } from "@/components/landing/HotelGroups";
import { ProofSection } from "@/components/landing/ProofSection";
import { VerdictSection } from "@/components/landing/VerdictSection";
import { SafetyBlock } from "@/components/landing/SafetyBlock";
import { Faq } from "@/components/landing/Faq";
import { FinalCta } from "@/components/landing/FinalCta";
import { Footer } from "@/components/landing/Footer";

interface SearchRequest {
  check_in?: string;
  check_out?: string;
}

export default async function Home() {
  const results: LandingResults & { search_request?: SearchRequest } = await getResults("demo");
  const tags = offersToTags(results);
  const groups = results.hotel_groups ?? [];

  const heroId = results.verdicts?.hero_hotel_id ?? groups[0]?.hotel_id;
  const heroTags = tags.filter((t) => t.hotelId === heroId);
  const pick = heroId ? results.verdicts?.per_hotel?.[heroId] : undefined;

  // The offer whose trail and gap we show: first verified offer of the hero hotel that has a price trail.
  const proofOffer = heroTags.find((t) => t.status === "verified" && t.price_trail.length > 0);

  const handoffId = pick?.best_for_you ?? pick?.safe_cheapest ?? undefined;
  const handoff: Handoff | null = handoffId ? await getHandoff(handoffId) : null;

  const platforms = Array.from(new Set(tags.map((t) => t.platform)));
  const events = (script as { events: StreamEvent[] }).events;

  return (
    <div className="tt">
      <NavBar />
      <main id="top">
        <Hero tags={heroTags} meta={results._meta} checkIn={results.search_request?.check_in} checkOut={results.search_request?.check_out} />
        <ProofStrip summary={results.summary_strip} sites={platforms.length} />
        <GapSection offer={proofOffer} />
        <HowItWorks />
        <LiveReplay tiles={heroTags} total={tags.length} events={events} />
        <HotelGroups groups={groups} tags={tags} />
        <ProofSection offer={proofOffer} />
        <VerdictSection
          hotelName={heroTags[0]?.groupName ?? heroTags[0]?.title}
          tags={tags}
          pick={pick}
          warnings={results.verdicts?.non_comparable_warnings ?? []}
          handoff={handoff}
        />
        <SafetyBlock />
        <Faq />
        <FinalCta />
      </main>
      <Footer platforms={platforms} />
    </div>
  );
}
