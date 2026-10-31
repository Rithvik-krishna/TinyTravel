"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import { getHandoff } from "@/lib/dataSource";
import { offersToTags } from "@/lib/tags";
import { Handoff } from "@/lib/landing";
import { useResults, useSearchId } from "@/lib/flow";
import { EmptyState, FlowShell, LoadingBlock } from "@/components/flow/FlowShell";
import { VerdictSection } from "@/components/landing/VerdictSection";
import { Provenance } from "@/components/landing/Provenance";
import { ReportLink } from "@/components/flow/ReportLink";

function Inner() {
  const { id, ready } = useSearchId();
  const { data, loading, error } = useResults(id);
  const tags = useMemo(() => offersToTags(data), [data]);
  const groups = data?.hotel_groups ?? [];
  const [hotel, setHotel] = useState<string | null>(null);
  const [handoff, setHandoff] = useState<Handoff | null>(null);

  // Only hotels that have offers can have a verdict; default to the hero hotel, else the first one with a pick.
  const withOffers = groups.filter((g) => tags.some((t) => t.hotelId === g.hotel_id));
  const hasPick = (hid?: string) => {
    const p = hid ? data?.verdicts?.per_hotel?.[hid] : undefined;
    return !!(p && (p.cheapest_verified || p.safe_cheapest || p.best_for_you));
  };
  const hero = data?.verdicts?.hero_hotel_id;
  const defaultHotel = (hero && withOffers.some((g) => g.hotel_id === hero) && hasPick(hero) ? hero : withOffers.find((g) => hasPick(g.hotel_id))?.hotel_id) ?? withOffers[0]?.hotel_id ?? null;
  const hotelId = hotel ?? defaultHotel;
  const pick = hotelId ? data?.verdicts?.per_hotel?.[hotelId] : undefined;
  const handoffId = pick?.best_for_you ?? pick?.safe_cheapest ?? null;

  useEffect(() => {
    let alive = true;
    setHandoff(null);
    if (handoffId) {
      getHandoff(handoffId)
        .then((h: Handoff) => alive && setHandoff(h))
        .catch(() => alive && setHandoff(null));
    }
    return () => {
      alive = false;
    };
  }, [handoffId]);

  if (ready && !id) return <EmptyState title="Start a search first" body="There's no verdict yet." />;
  if (loading || !ready) return <main className="page"><div className="wrap"><LoadingBlock label="Loading verdict" /></div></main>;
  if (error || !data) return <main className="page"><div className="wrap"><div className="notice bad" role="alert">{error ?? "No results."}</div></div></main>;

  const hotelTags = tags.filter((t) => t.hotelId === hotelId);
  const name = groups.find((g) => g.hotel_id === hotelId)?.canonical_name ?? hotelTags[0]?.title;
  // Only show a handoff that belongs to the offer we are recommending.
  const shownHandoff = handoff && handoff.offer_id === handoffId ? handoff : null;

  return (
    <main>
      <div className="wrap" style={{ paddingTop: 28 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 10 }}>
          <Provenance meta={data._meta} />
          {withOffers.length > 1 && (
            <div className="seg" role="group" aria-label="Hotel">
              {withOffers.map((g) => (
                <button key={g.hotel_id} type="button" aria-pressed={g.hotel_id === hotelId} onClick={() => setHotel(g.hotel_id ?? null)}>{g.canonical_name}</button>
              ))}
            </div>
          )}
        </div>
      </div>
      {data.complete !== false && <div className="wrap" style={{ paddingTop: 12 }}><ReportLink searchId={id} /></div>}
      {data.complete === false && <div className="wrap" style={{ paddingTop: 16 }}><div className="notice warn" role="status">The investigation is still running, so the verdict is not final yet.</div></div>}
      {pick && data.complete !== false && (pick.cheapest_verified || pick.safe_cheapest || pick.best_for_you) ? (
        <VerdictSection hotelName={name} tags={tags} pick={pick} warnings={data.verdicts?.non_comparable_warnings ?? []} handoff={shownHandoff} searchId={id} />
      ) : data.complete === false ? null : (
        <div className="wrap" style={{ paddingBlock: 40 }}>
          <div className="notice warn">No offer was verified at the payment page for this hotel, so we don&apos;t name a pick. The results page shows what was found.</div>
        </div>
      )}
    </main>
  );
}

export default function Page() {
  return (
    <FlowShell>
      <Suspense fallback={<main className="page"><div className="wrap"><LoadingBlock /></div></main>}>
        <Inner />
      </Suspense>
    </FlowShell>
  );
}