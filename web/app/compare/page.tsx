"use client";

import React, { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { offersToTags, TagItem } from "@/lib/tags";
import { useResults, useSearchId, withId } from "@/lib/flow";
import { EmptyState, FlowShell, LoadingBlock } from "@/components/flow/FlowShell";
import { OfferCard } from "@/components/flow/OfferCard";
import { Provenance } from "@/components/landing/Provenance";

const rank = (t: TagItem) => (t.status === "verified" && t.payable != null ? 0 : t.status === "unverified" ? 1 : 2);
const byPayable = (a: TagItem, b: TagItem) => rank(a) - rank(b) || (a.payable ?? Infinity) - (b.payable ?? Infinity);

function Inner() {
  const { id, ready } = useSearchId();
  const { data, loading, error } = useResults(id);
  const [mode, setMode] = useState<"hotel" | "all">("hotel");
  const [hideNc, setHideNc] = useState(false);
  const tags = useMemo(() => offersToTags(data), [data]);
  const warnings = data?.verdicts?.non_comparable_warnings ?? [];
  const ncIds = new Set(warnings.map((w) => w.offer_id));
  const groups = data?.hotel_groups ?? [];

  if (ready && !id) return <EmptyState title="Start a search first" body="There are no results to compare yet." />;
  if (loading || !ready) return <main className="page"><div className="wrap"><LoadingBlock label="Loading results" /></div></main>;
  if (error || !data) return <main className="page"><div className="wrap"><div className="notice bad" role="alert">{error ?? "No results."}</div></div></main>;

  const visible = (t: TagItem) => !(hideNc && ncIds.has(t.id));
  const verifiedCount = tags.filter((t) => t.status === "verified").length;

  return (
    <main className="page">
      <div className="wrap">
        <div className="page-head">
          <span className="eyebrow">Step 3 of 5</span>
          <h1>Every hotel we checked</h1>
          <p className="lede">Listing price against the price at the payment page, observed on this run. Blocked and unverified offers stay visible with the reason and never get a price or a score.</p>
          <div className="row">
            <Provenance meta={data._meta} />
            <div className="seg" role="group" aria-label="View">
              <button type="button" aria-pressed={mode === "hotel"} onClick={() => setMode("hotel")}>Per hotel</button>
              <button type="button" aria-pressed={mode === "all"} onClick={() => setMode("all")}>All offers by price</button>
            </div>
            {ncIds.size > 0 && (
              <button type="button" className="chip-btn" aria-pressed={hideNc} onClick={() => setHideNc((v) => !v)}>Hide non-comparable</button>
            )}
          </div>
        </div>

        {verifiedCount === 0 && <div className="notice warn" style={{ marginBottom: 20 }}>No offer was verified at the payment page, so no price is highlighted.</div>}

        {mode === "all" ? (
          <div className="offers">
            {[...tags].filter(visible).sort(byPayable).map((t) => (
              <OfferCard key={t.id} t={t} searchId={id} scaleMax={Math.max(...tags.map((x) => Math.max(x.listing ?? 0, x.payable ?? 0)))} notComparable={ncIds.has(t.id)} showHotel />
            ))}
          </div>
        ) : (
          groups.map((g) => {
            const merged = g.match_status === "merged";
            const items = tags.filter((t) => (g.offer_ids ? g.offer_ids.includes(t.id) : t.hotelId === g.hotel_id)).filter(visible).sort(byPayable);
            const pick = g.hotel_id ? data.verdicts?.per_hotel?.[g.hotel_id] : undefined;
            const scaleMax = Math.max(0, ...items.map((x) => Math.max(x.listing ?? 0, x.payable ?? 0)));
            const gw = warnings.filter((w) => w.hotel_id === g.hotel_id || (w.offer_id && g.offer_ids?.includes(w.offer_id)));
            const conf = g.confidence != null ? Math.round(g.confidence * 100) : null;
            return (
              <div key={g.hotel_id ?? g.canonical_name} className={`hotel-card${merged ? "" : " suggested"}`}>
                <div className="hh">
                  <h2>{g.canonical_name}</h2>
                  {g.area && <span className="mono" style={{ color: "var(--muted)", fontSize: 13 }}>{g.area}</span>}
                  {merged ? <span className="badge ok">Same hotel{conf != null ? ` · ${conf}%` : ""}</span> : <span className="badge warn">Possible match, not merged in pricing{conf != null ? ` · ${conf}%` : ""}</span>}
                </div>
                {g.why && <p className="gwhy" style={{ color: "var(--muted)", fontSize: 14 }}>Why grouped: {g.why}</p>}
                {gw.map((w) => <div className="notice warn" key={w.offer_id}>{w.message}</div>)}
                {items.every((t) => t.status !== "verified") && items.length > 0 && <div className="notice">No verified offer for this hotel, so there is no price to rank.</div>}
                <div className="offers">
                  {items.map((t) => {
                    const labels = merged && pick ? [pick.cheapest_verified === t.id && "Cheapest verified", pick.safe_cheapest === t.id && "Safe-cheapest"].filter((x): x is string => !!x) : [];
                    return <OfferCard key={t.id} t={t} searchId={id} scaleMax={scaleMax} labels={labels} notComparable={ncIds.has(t.id)} />;
                  })}
                </div>
              </div>
            );
          })
        )}

        <div className="cta-bar">
          <Link className="btn" href={withId("/verdict", id)}>See verdict</Link>
          <Link className="btn ghost" href={withId("/evidence", id)}>See proof</Link>
        </div>
      </div>
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
