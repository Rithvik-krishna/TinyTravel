"use client";

import React, { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getResults, MOCK, openStream, startSearch } from "@/lib/dataSource";
import { inr } from "@/lib/format";
import { offersToTags, blockerLabel, siteLabel, TagItem } from "@/lib/tags";
import { buildSentence, loadRequest, saveSearch, stayLabel, useResults, useSearchId, withId } from "@/lib/flow";
import { AgentState, countsOf, emptyStream, Phase, useInvestigationStream } from "@/lib/useInvestigationStream";
import { EmptyState, FlowShell, LoadingBlock } from "@/components/flow/FlowShell";
import { Provenance } from "@/components/landing/Provenance";


const PHASE_TEXT: Record<Phase, string> = {
  idle: "Getting ready",
  parsing: "Reading your request",
  discovering: "Finding listings on 3 sites",
  grouping: "Matching the same hotel across sites",
  verifying: "Checking each site like a real buyer. This can take several minutes.",
  done: "Investigation complete",
  error: "The investigation hit an error",
};

const SHOW_DEV = process.env.NEXT_PUBLIC_SHOW_PROVENANCE === "1";
const siteName = siteLabel;
const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
const safeUrl = (u: string) => (/^(https?:\/\/|\/)/.test(u) ? u : "");

function Tile({ a, tag }: { a: AgentState; tag?: TagItem }) {
  const done = a.status !== "running";
  // Real agents report an unpredictable number of steps, so the bar eases toward 92% instead of assuming a total.
  const width = done ? 100 : Math.min(92, 8 + a.steps * 3);
  const badge = a.status === "verified" ? "ok" : a.status === "blocked" ? "bad" : a.status === "unverified" ? "warn" : "";
  const url = safeUrl(a.streamingUrl);
  // Same-origin views embed; external live-view links are opened in a new tab instead of leaving a blank frame.
  const embed = url.startsWith("/");
  return (
    <div className={`itile ${a.status}`}>
      <div className="ihead">
        <b>{siteName(a.platform)}</b>
        <span className={`badge ${badge}`}>{a.status}</span>
      </div>
      {embed && <iframe src={url} title={`${a.platform} checkout view for ${a.hotel}`} loading="lazy" sandbox="allow-scripts" />}
      <div className="ibody">
        <div className="st">{a.stepText ?? "Starting"}</div>
        <div className="prog"><i style={{ width: `${width}%` }} /></div>
        <div className="meta">
          <span>{done ? "finished" : `${a.steps} step${a.steps === 1 ? "" : "s"} so far`}</span>
          {url && !done && <a href={url} target="_blank" rel="noopener noreferrer" style={{ textDecoration: "underline" }}>Watch live view ↗</a>}
        </div>
        {a.status === "verified" && tag?.payable != null && (
          <div className="pay">
            {inr(tag.payable, tag.currency)}
            {tag.listing != null && <s>listing {inr(tag.listing, tag.currency)}</s>}
          </div>
        )}
        {a.status === "blocked" && <p style={{ color: "var(--muted)", fontSize: 14 }}>{blockerLabel(tag?.blocker)}. {tag?.blocker === "captcha" || tag?.blocker === "login" || tag?.blocker === "otp" ? "We never solve captchas, log in or enter an OTP, so there is no price for this one." : "No price was captured for this site."}</p>}
        {a.status === "unverified" && <p style={{ color: "var(--muted)", fontSize: 14 }}>Not verified: no payable price was captured.</p>}
      </div>
    </div>
  );
}

function Inner() {
  const { id, ready } = useSearchId();
  const [speed, setSpeed] = useState(2);
  const [elapsed, setElapsed] = useState(0);
  const [run, setRun] = useState(0);
  const [summary, setSummary] = useState("");
  // Set when the service does not know this search id (old link, wrong data mode), so we stop waiting.
  const [missing, setMissing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState("");
  // Starts the same search again from the saved request (one click after a search that found nothing).
  const searchAgain = async () => {
    const r = loadRequest();
    if (!r) {
      window.location.href = "/book";
      return;
    }
    setRetrying(true);
    setRetryError("");
    try {
      const { raw_text: _raw, ...fields } = r;
      void _raw;
      const res: { search_id?: string } = await startSearch("", fields);
      if (!res?.search_id) throw new Error("no id");
      saveSearch({ ...r, raw_text: buildSentence(r) }, res.search_id);
      window.location.href = `/investigation?id=${encodeURIComponent(res.search_id)}`;
    } catch {
      setRetrying(false);
      setRetryError("Could not start the search again. Check that the booking service is running.");
    }
  };
  useEffect(() => {
    const r = loadRequest();
    if (r) setSummary(`${r.destination} · ${stayLabel({ check_in: r.check_in, check_out: r.check_out, guests: r.guests })}`);
  }, []);

  const open = useCallback(
    (onEvent: (event: string, data: unknown) => void) => openStream(id ?? "mock_search", onEvent, MOCK ? speed : 1),
    [id, speed],
  );
  const { state, start } = useInvestigationStream(open, emptyStream, { finalOnReducedMotion: false });

  useEffect(() => {
    if (ready && id) {
      setElapsed(0);
      start();
    }
  }, [ready, id, run, start]);

  const finished = state.phase === "done" || state.phase === "error";
  useEffect(() => {
    if (finished || !ready || !id) return;
    const t = window.setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => window.clearInterval(t);
  }, [finished, ready, id, run]);

  useEffect(() => {
    if (!id || MOCK || state.phase !== "idle") return;
    const t = window.setTimeout(() => {
      getResults(id)
        .then((r: { detail?: unknown; offers?: unknown }) => {
          if (!r || r.detail || !Array.isArray(r.offers)) setMissing(true);
        })
        .catch(() => setMissing(true));
    }, 6000);
    return () => window.clearTimeout(t);
  }, [id, state.phase, run]);

  const results = useResults(id, MOCK || state.phase === "done");
  const tags = useMemo(() => offersToTags(results.data), [results.data]);
  const agents = Object.values(state.agents);
  const total = Math.max(tags.length, agents.length);
  const siteCount = new Set(agents.map((a) => siteName(a.platform))).size;
  const c = countsOf(state, total);

  const groups = useMemo(() => {
    const m = new Map<string, { name: string; agents: AgentState[] }>();
    for (const a of agents) {
      const t = tags.find((x) => x.id === a.offerId);
      const key = t?.hotelId || a.hotel;
      const name = t?.groupName || a.hotel;
      m.set(key, { name, agents: [...(m.get(key)?.agents ?? []), a] });
    }
    return Array.from(m.values());
  }, [agents, tags]);

  if (ready && !id) return <EmptyState title="Start a search first" body="There's no investigation to show yet." />;

  const story =
    state.phase === "verifying"
      ? `${c.running} of ${total || agents.length} agents are still working. ${c.verified + c.unverified + c.blocked} finished.`
      : state.phase === "done"
        ? `All agents finished: ${c.verified} verified, ${c.unverified} unverified, ${c.blocked} blocked.`
        : "";

  return (
    <main className="page">
      <div className="wrap">
        <div className="page-head">
          <h1>{siteCount > 0 ? `Checking prices on ${siteCount} site${siteCount === 1 ? "" : "s"}` : "Checking prices"}</h1>
          <p className="lede">
            {summary ? `${summary}. ` : ""}Each agent opens a site as a guest, picks the room, fills in placeholder guest details and stops at the payment page, so you see the real total. Nothing is booked.
          </p>
          <div className="row"><Provenance meta={results.data?._meta} /></div>
        </div>

        <div className="statusbar">
          <span className="phase" role="status">{PHASE_TEXT[state.phase]}</span>
          <span className="clock" aria-label="Elapsed time">{clock(elapsed)}</span>
        </div>
        <div className="counters" aria-live="polite" style={{ marginBottom: 14 }}>
          <div><b>{state.listings ?? "–"}</b><span>listings</span></div>
          <div><b>{state.hotels ?? "–"}</b><span>hotels</span></div>
          <div><b>{c.verified}</b><span>verified</span></div>
          <div><b>{c.unverified}</b><span>unverified</span></div>
          <div><b>{c.blocked}</b><span>blocked</span></div>
          <div><b>{c.running}</b><span>running</span></div>
        </div>
        {state.phase === "done" && agents.length === 0 ? (
          <div className="notice warn" role="status" style={{ marginBottom: 20 }}>
            <strong>No hotels were found for this search.</strong> The run finished without finding any listings on Cleartrip, Agoda or Booking.com, so there is nothing to compare and no price is shown. The sites may not have answered in time. Try again, or change the destination or dates.{" "}
            <Link className="linkish" href="/book">Start a new search</Link>
          </div>
        ) : (
          story && <p className="story">{story}</p>
        )}

        {state.phase === "error" && (
          <div className="notice bad" role="alert" style={{ marginBottom: 20 }}>
            <strong>Something went wrong.</strong> {state.error}{" "}
            {state.recoverable ? (
              <button className="linkish" type="button" onClick={() => setRun((r) => r + 1)}>Try again</button>
            ) : (
              <Link className="linkish" href="/book">Start a new search</Link>
            )}
          </div>
        )}

        {missing && agents.length === 0 && (
          <div className="notice bad" role="alert" style={{ marginBottom: 16 }}>
            We could not find this search. The link may be old, or it was made in a different data mode.{" "}
            <Link className="linkish" href="/book">Start a new search</Link>
          </div>
        )}
        {!missing && agents.length === 0 && !finished && elapsed > 15 && (
          <div className="notice" role="status" style={{ marginBottom: 16 }}>
            Finding hotels on each site first. With real browser agents this step alone can take 3 to 5 minutes, and nothing is shown until it finishes.
          </div>
        )}
        {!finished && elapsed > 600 && (
          <div className="notice warn" role="status" style={{ marginBottom: 16 }}>
            This is taking longer than usual ({Math.floor(elapsed / 60)} minutes). Real runs usually finish in 5 to 15 minutes. You can leave this page and come back to the same link later; results fill in as agents finish.{" "}
            <Link className="linkish" href="/book">Start a new search</Link>
          </div>
        )}
        {agents.length === 0 && state.phase !== "error" && <LoadingBlock label="Waiting for agents to start" />}

        {groups.map((g) => (
          <section className="hgroup" key={g.name} style={{ padding: 0 }}>
            <h2>{g.name}</h2>
            <div className="itiles">
              {g.agents.map((a) => (
                <Tile key={a.runId} a={a} tag={tags.find((t) => t.id === a.offerId)} />
              ))}
            </div>
          </section>
        ))}

        <div className="cta-bar">
          {!finished && (state.hotels ?? 0) > 0 && (
            <Link className="btn ghost" href={withId("/compare", id)}>See results so far</Link>
          )}
          {state.phase === "done" && agents.length === 0 ? (
            <>
              <button className="btn" type="button" onClick={searchAgain} disabled={retrying}>{retrying ? "Starting…" : "Search again"}</button>
              <Link className="btn ghost" href="/book">Change the search</Link>
              {retryError && <span className="fine" role="alert">{retryError}</span>}
            </>
          ) : state.phase === "done" ? (
            <>
              <Link className="btn" href={withId("/compare", id)}>See results</Link>
              <Link className="btn ghost" href={withId("/verdict", id)}>Go to verdict</Link>
            </>
          ) : (
            null
          )}
          {SHOW_DEV && MOCK && (
            <div className="tools" style={{ marginLeft: "auto" }}>
              <label htmlFor="spd" className="lab mono" style={{ color: "var(--muted)", fontSize: 12 }}>Replay speed</label>
              <select id="spd" value={speed} onChange={(e) => setSpeed(Number(e.target.value))}>
                <option value={1}>1x</option>
                <option value={2}>2x</option>
                <option value={4}>4x</option>
              </select>
              <button className="btn ghost sm" type="button" onClick={() => setRun((r) => r + 1)}>Restart</button>
            </div>
          )}
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