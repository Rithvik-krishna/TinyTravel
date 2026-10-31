"use client";

import React, { Suspense, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { offersToTags, blockerLabel, TagItem } from "@/lib/tags";
import { inr, shortTime } from "@/lib/format";
import { useResults, useSearchId, withId } from "@/lib/flow";
import { EmptyState, FlowShell, LoadingBlock } from "@/components/flow/FlowShell";
import { PriceTrail } from "@/components/landing/PriceTrail";
import { FeeBreakdown } from "@/components/landing/FeeBreakdown";
import { Provenance } from "@/components/landing/Provenance";

interface RawOffer {
  offer_id?: string;
  steps?: number;
  cost_usd?: number | null;
  run_id?: string;
  furthest_step?: string | null;
  max_occupancy?: number | null;
}

function Inner() {
  const { id, ready } = useSearchId();
  const router = useRouter();
  const wanted = useSearchParams().get("offer");
  const { data, loading, error } = useResults(id);
  const tags = useMemo(() => offersToTags(data), [data]);

  if (ready && !id) return <EmptyState title="Start a search first" body="There's no proof to show yet." />;
  if (loading || !ready) return <main className="page"><div className="wrap"><LoadingBlock label="Loading proof" /></div></main>;
  if (error || !data) return <main className="page"><div className="wrap"><div className="notice bad" role="alert">{error ?? "No results."}</div></div></main>;

  const heroId = data.verdicts?.hero_hotel_id;
  const best = heroId ? data.verdicts?.per_hotel?.[heroId]?.best_for_you : undefined;
  const offer: TagItem | undefined = tags.find((t) => t.id === wanted) ?? tags.find((t) => t.id === best) ?? tags.find((t) => t.status === "verified") ?? tags[0];
  if (!offer) return <EmptyState title="No offers" body="This search has no offers to show proof for." />;

  const raw = (Array.isArray(data.offers) ? (data.offers as RawOffer[]) : []).find((o) => o.offer_id === offer.id);
  const verified = offer.status === "verified" && offer.payable != null;
  const groups = data.hotel_groups ?? [];
  const pressure = offer.urgency_or_scarcity_messages;
  const addons = offer.preselected_addons;
  const at = shortTime(offer.verifiedAt);

  return (
    <main className="page">
      <div className="wrap">
        <div className="page-head">
          <span className="eyebrow">Step 4 of 5</span>
          <h1>Every number links to its page</h1>
          <div className="row"><Provenance meta={data._meta} /></div>
        </div>

        <div className="picker">
          <label htmlFor="pick" className="lab mono" style={{ color: "var(--muted)", fontSize: 12 }}>Offer</label>
          <select id="pick" value={offer.id} onChange={(e) => router.replace(`${withId("/evidence", id)}${id ? "&" : "?"}offer=${encodeURIComponent(e.target.value)}`)}>
            {groups.map((g) => (
              <optgroup key={g.hotel_id} label={g.canonical_name}>
                {tags.filter((t) => (g.offer_ids ? g.offer_ids.includes(t.id) : t.hotelId === g.hotel_id)).map((t) => (
                  <option key={t.id} value={t.id}>{t.platform} · {t.status}{t.payable != null ? ` · ${inr(t.payable, t.currency)}` : ""}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </div>

        {verified ? (
          <div className="proof">
            <PriceTrail key={offer.id} offer={offer} />
            <FeeBreakdown offer={offer} />
          </div>
        ) : (
          <div className="facts">
            <h2 style={{ fontSize: 22 }}>{offer.status === "blocked" ? "This run was blocked" : "This price was not verified"}</h2>
            <p className="lede">
              {offer.status === "blocked" ? `${blockerLabel(offer.blocker)}. We never solve captchas, log in or enter an OTP.` : "No payable price was captured at the payment page."}{" "}
              There is no fee gap and no score for this offer.
            </p>
            <dl>
              <div><dt>Furthest step</dt><dd>{raw?.furthest_step ?? "N/A"}</dd></div>
              <div><dt>Listing price</dt><dd>{inr(offer.listing, offer.currency)}</dd></div>
              <div><dt>Payable price</dt><dd>N/A</dd></div>
            </dl>
            {offer.price_trail.length > 0 && <PriceTrail key={offer.id} offer={offer} />}
          </div>
        )}

        <div className="facts">
          <h2 style={{ fontSize: 20 }}>Offer facts</h2>
          <dl>
            <div><dt>Hotel</dt><dd>{offer.title}</dd></div>
            <div><dt>Site</dt><dd>{offer.platform}</dd></div>
            {offer.room_type && <div><dt>Room</dt><dd>{offer.room_type}</dd></div>}
            {raw?.max_occupancy != null && <div><dt>Occupancy</dt><dd>{raw.max_occupancy}</dd></div>}
            {offer.meal_plan && <div><dt>Meal plan</dt><dd>{offer.meal_plan}</dd></div>}
            {offer.cancellation_policy && <div><dt>Cancellation</dt><dd>{offer.cancellation_policy}</dd></div>}
          </dl>
          {pressure.length > 0 && (
            <div className="tags">{pressure.map((m) => <span className="badge" key={m}>Site message: {m}</span>)}</div>
          )}
          {addons.length > 0 && (
            <div className="tags">{addons.map((a, i) => <span className="badge" key={i}>Pre-selected by the site: {typeof a === "string" ? a : JSON.stringify(a)}</span>)}</div>
          )}
          <p className="note" style={{ marginTop: 4 }}>
            {[raw?.steps != null && `${raw.steps} steps checked`, at && `verified at ${at}`].filter(Boolean).join(" · ")}
          </p>
        </div>

        <div className="cta-bar">
          <Link className="btn" href={withId("/verdict", id)}>See verdict</Link>
          <Link className="btn ghost" href={withId("/compare", id)}>Back to results</Link>
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
