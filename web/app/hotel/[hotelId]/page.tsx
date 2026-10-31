"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { getHandoff } from "@/lib/dataSource";
import { inr, shortTime } from "@/lib/format";
import { stayLabel, useResults, useSearchId, withId } from "@/lib/flow";
import { Handoff } from "@/lib/landing";
import { blockerLabel, offersToTags, TagItem } from "@/lib/tags";
import { EmptyState, FlowShell, LoadingBlock } from "@/components/flow/FlowShell";
import { HotelArt } from "@/components/flow/HotelArt";
import { HandoffDialog } from "@/components/flow/HandoffDialog";
import { PriceTrail } from "@/components/landing/PriceTrail";
import { FeeBreakdown } from "@/components/landing/FeeBreakdown";
import { Provenance } from "@/components/landing/Provenance";

const rank = (t: TagItem) => (t.status === "verified" && t.payable != null ? 0 : t.status === "unverified" ? 1 : 2);

function cancelBadge(t: TagItem) {
  if (t.cancellation_category === "free") return <span className="badge ok">Free cancellation</span>;
  if (t.cancellation_category === "non_refundable") return <span className="badge warn">Non-refundable</span>;
  return <span className="badge warn">Partial refund</span>;
}

function Inner() {
  const { id, ready } = useSearchId();
  const { hotelId } = useParams<{ hotelId: string }>();
  const wanted = useSearchParams().get("offer");
  const { data, loading, error } = useResults(id);
  const tags = useMemo(() => offersToTags(data), [data]);
  const [picked, setPicked] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [handoff, setHandoff] = useState<Handoff | null>(null);

  const offers = useMemo(
    () => tags.filter((t) => t.hotelId === hotelId).sort((a, b) => rank(a) - rank(b) || (a.payable ?? 0) - (b.payable ?? 0)),
    [tags, hotelId],
  );
  const verified = offers.filter((t) => t.status === "verified" && t.payable != null);
  const best = data?.verdicts?.per_hotel?.[hotelId]?.best_for_you;
  const selId = picked ?? (wanted && verified.some((t) => t.id === wanted) ? wanted : null) ?? (best && verified.some((t) => t.id === best) ? best : null) ?? verified[0]?.id ?? null;
  const sel = offers.find((t) => t.id === selId);

  useEffect(() => {
    let alive = true;
    setHandoff(null);
    if (selId) {
      getHandoff(selId)
        .then((h: Handoff) => alive && setHandoff(h))
        .catch(() => alive && setHandoff(null));
    }
    return () => {
      alive = false;
    };
  }, [selId]);

  if (ready && !id) return <EmptyState title="Start a search first" body="There's no hotel to show yet." />;
  if (loading || !ready) return <main className="page"><div className="wrap"><LoadingBlock label="Loading hotel" /></div></main>;
  if (error || !data) return <main className="page"><div className="wrap"><div className="notice bad" role="alert">{error ?? "No results."}</div></div></main>;
  if (offers.length === 0) return <EmptyState title="Hotel not found" body="This hotel isn't part of this search." href={withId("/compare", id)} cta="Back to results" />;

  const group = data.hotel_groups?.find((g) => g.hotel_id === hotelId);
  const info = data.hotels?.find((h) => h.hotel_id === hotelId);
  const name = group?.canonical_name ?? info?.canonical_name ?? offers[0].title;
  const area = group?.area ?? info?.area;
  const stay = stayLabel(data.search_request);
  const warn = data.verdicts?.non_comparable_warnings?.find((w) => w.offer_id === selId);
  const minPay = verified.length ? Math.min(...verified.map((t) => t.payable as number)) : null;
  const at = shortTime(sel?.verifiedAt);

  return (
    <main className="page hotel-page">
      <div className="wrap">
        <div className="back">
          <Link className="linkish" href={withId("/compare", id)}>← Back to results</Link>
        </div>

        <div className="dhead">
          <div className="art"><HotelArt hotelId={hotelId} name={name} /></div>
          <div className="hb">
            <h1>{name}</h1>
            <div className="hmeta">
              {info?.rating != null && <span>★ {info.rating.toFixed(1)}</span>}
              {area && <span>{area}</span>}
              {stay && <span>{stay}</span>}
              <Provenance meta={data._meta} />
            </div>
          </div>
        </div>

        <div className="dlayout">
          <div>
            <div className="dsec">
              <h2>Compare sites</h2>
              <p className="muted">Totals are what we saw on the payment page. Pick one to see how the price built up.</p>
              <div className="orows" role="radiogroup" aria-label="Offers">
                {offers.map((t) => {
                  const ok = t.status === "verified" && t.payable != null;
                  const sub = ok
                    ? `${t.cancellation_policy ?? ""}${t.cancellation_policy ? " · " : ""}verified ${shortTime(t.verifiedAt)}`
                    : t.status === "blocked"
                      ? `${blockerLabel(t.blocker)}. No total was confirmed.`
                      : "Couldn't verify: no total was confirmed at the payment page.";
                  return (
                    <div
                      key={t.id}
                      className="orow"
                      role="radio"
                      tabIndex={ok ? 0 : -1}
                      aria-checked={t.id === selId}
                      aria-disabled={!ok}
                      onClick={() => ok && setPicked(t.id)}
                      onKeyDown={(e) => {
                        if (ok && (e.key === "Enter" || e.key === " ")) {
                          e.preventDefault();
                          setPicked(t.id);
                        }
                      }}
                    >
                      <span className="radio" />
                      <div>
                        <b className="pf">{t.platform}</b>{" "}
                        {ok && t.payable === minPay && <span className="badge ok">Lowest</span>}{" "}
                        {ok && t.id === best && <span className="badge ok">Best for you</span>}{" "}
                        {t.cancellation_category === "non_refundable" && ok && <span className="badge warn">Non-refundable</span>}
                        <div className="sub">{sub}</div>
                      </div>
                      <div className="oamt">
                        {ok ? (
                          <>
                            <div className="price">{inr(t.payable)}</div>
                            <div className="sub">listed {inr(t.listing)}</div>
                          </>
                        ) : (
                          <div className="sub">No price</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              {warn?.message && <div className="notice warn">{warn.message}</div>}
            </div>

            {sel && (
              <>
                <div className="dsec">
                  <h2>How the price built up</h2>
                  <PriceTrail key={sel.id} offer={sel} />
                  <p className="fine">Tap an amount to see the evidence from that step. Observed on this run; we don&apos;t claim why a price moved.</p>
                </div>
                <div className="dsec">
                  <h2>Price breakdown</h2>
                  <FeeBreakdown offer={sel} />
                </div>
                <div className="dsec">
                  <h2>Room details</h2>
                  <div className="sumcard">
                    <dl>
                      {sel.room_type && (<><dt>Room</dt><dd>{sel.room_type}</dd></>)}
                      {sel.meal_plan && (<><dt>Meals</dt><dd>{sel.meal_plan}</dd></>)}
                      {sel.cancellation_policy && (<><dt>Cancellation</dt><dd>{sel.cancellation_policy}</dd></>)}
                      {at && (<><dt>Checked</dt><dd>{at}</dd></>)}
                      {sel.urgency_or_scarcity_messages.length > 0 && (
                        <><dt>Site messages</dt><dd>{sel.urgency_or_scarcity_messages.map((m) => <span className="badge" style={{ margin: "0 6px 6px 0" }} key={m}>{m}</span>)}</dd></>
                      )}
                      {sel.preselected_addons.length > 0 && (
                        <><dt>Add-ons</dt><dd>{sel.preselected_addons.map((a, i) => <div key={i}>{typeof a === "string" ? a : JSON.stringify(a)}</div>)}</dd></>
                      )}
                      <dt>Proof</dt>
                      <dd><Link className="linkish" href={`${withId("/evidence", id)}${id ? "&" : "?"}offer=${encodeURIComponent(sel.id)}`}>Open the full proof page</Link></dd>
                    </dl>
                  </div>
                </div>
              </>
            )}
            {!sel && <div className="notice warn">No verified offer for this hotel, so there is no price to book.</div>}
          </div>

          {sel && (
            <aside className="aside" aria-label="Your selection">
              <span className="fine" style={{ fontWeight: 600 }}>Total on {sel.platform}</span>
              <div className="price">{inr(sel.payable)}</div>
              <div className="hmeta">
                {sel.listing != null && <s>listed {inr(sel.listing)}</s>}
                {sel.fee_leak_pct != null && <span className="badge">+{sel.fee_leak_pct}%</span>}
              </div>
              {cancelBadge(sel)}
              <button className="btn" type="button" onClick={() => setOpen(true)}>Continue on {sel.platform}</button>
              <p className="fine">You pay on {sel.platform}. TinyTravel never takes payment.{at ? ` Verified ${at};` : ""} prices can change.</p>
            </aside>
          )}
        </div>
      </div>

      {sel && (
        <>
          <div className="sticky-bar">
            <div>
              <div className="price">{inr(sel.payable)}</div>
              <div className="fine">total on {sel.platform}</div>
            </div>
            <button className="btn" type="button" onClick={() => setOpen(true)}>Continue on {sel.platform}</button>
          </div>
          <HandoffDialog open={open} onClose={() => setOpen(false)} offer={sel} hotelName={name} stay={stay} handoff={handoff} />
        </>
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
