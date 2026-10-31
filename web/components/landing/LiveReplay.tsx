"use client";

import React, { useCallback, useEffect, useMemo, useRef } from "react";
import { inr } from "@/lib/format";
import { TagItem } from "@/lib/tags";
import { countsOf, emptyStream, replayAll, StreamEvent, useInvestigationStream } from "@/lib/useInvestigationStream";

/** Steps an agent reports before the payment page; only used to scale the progress bar. */
const STEP_TOTAL = 6;

interface Props {
  tiles: TagItem[];
  total: number;
  /** Script events (mock only); the finished run is computed from them so SSR and reduced-motion show the end state. */
  events: StreamEvent[];
}

export function LiveReplay({ tiles, total, events }: Props) {
  const finalState = useMemo(() => replayAll(events), [events]);
  const open = useCallback(
    // The landing replay always plays the bundled sample script locally at 2x, independent of the data mode.
    (onEvent: (event: string, data: unknown) => void) => {
      const timers = (events as Array<StreamEvent & { t_ms?: number }>).map((ev) => window.setTimeout(() => onEvent(ev.event, ev.data), (ev.t_ms ?? 0) / 2));
      return () => timers.forEach(clearTimeout);
    },
    [events],
  );
  const { state, start } = useInvestigationStream(open, finalState);
  const box = useRef<HTMLDivElement>(null);
  const started = useRef(false);
  const c = countsOf(state, total);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) {
      started.current = true;
      start();
      return;
    }
    const io = new IntersectionObserver(
      (es, ob) => {
        if (es[0].isIntersecting && !started.current) {
          started.current = true;
          start();
          ob.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [start]);

  const agents = Object.values(state.agents);

  return (
    <section id="live">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">Watch it verify</span>
          <h2>Agents at checkout.</h2>
          <p className="lede">
            Each agent opens a site, picks the room, fills in guest details and stops at the payment page. Several run in parallel; the ones for {tiles[0]?.groupName ?? tiles[0]?.title ?? "one hotel"} are shown.
          </p>
        </div>
        <div className="live">
          <div className="live-top">
            <div className="counters" aria-live="polite">
              <div><b>{c.verified}</b><span>verified</span></div>
              <div><b>{c.unverified}</b><span>unverified</span></div>
              <div><b>{c.blocked}</b><span>blocked</span></div>
              <div><b>{c.running}</b><span>running</span></div>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              
              <button className="btn ghost sm" type="button" onClick={start}>Restart</button>
            </div>
          </div>
          <div className="tiles" ref={box}>
            {tiles.map((t) => {
              const a = agents.find((x) => x.offerId === t.id);
              const done = a != null && a.status !== "running";
              const verified = a?.status === "verified";
              const width = !a ? 0 : done ? 100 : Math.round((a.steps / STEP_TOTAL) * 92);
              const text = !a ? "Waiting to start" : a.stepText ?? "Starting";
              const res = !a || !done ? "" : verified ? `Verified · ${inr(t.payable, t.currency)}` : a.status === "blocked" ? `Blocked · ${t.blocker ?? "other"}` : "Not verified";
              return (
                <div className={`tile${verified ? " done" : ""}`} key={t.id}>
                  <div className="bar">
                    <i /><i /><i />
                    <span>checkout · {t.platform.toLowerCase().replace(".com", "")}</span>
                  </div>
                  <div className="body">
                    <div className="plat">{t.platform}</div>
                    <div className="step-text">{text}</div>
                    <div className="prog"><i style={{ width: `${width}%` }} /></div>
                    <div className="res">{res}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}