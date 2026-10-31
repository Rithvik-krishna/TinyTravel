"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { blockerLabel, TagItem } from "@/lib/tags";
import { gapAmount, gapPct, inr, shortTime } from "@/lib/format";

/** Per-tag pendulum state: angle in degrees, angular velocity. */
interface Swinger {
  a: number;
  v: number;
}

const MAX_ANGLE = 14;
const SPRING = 46;
const DAMPING = 2.2;

function cancelHint(c: TagItem["cancellation_category"]): string {
  return c === "free" ? "Free cancellation" : c === "partial" ? "Partial refund" : "Non-refundable";
}

function Stamp({ tag }: { tag: TagItem }) {
  if (tag.status === "verified") {
    const t = shortTime(tag.verifiedAt);
    return <span className="stamp ok">{t ? `Verified ${t}` : "Verified"}</span>;
  }
  if (tag.status === "blocked") return <span className="stamp bad">🔒 {blockerLabel(tag.blocker)}</span>;
  return <span className="stamp warn">Not verified</span>;
}

interface TagProps {
  tag: TagItem;
  width: string;
  index: number;
  setNode: (i: number, el: HTMLDivElement | null) => void;
  kick: (i: number, v: number) => void;
}

function HangingTag({ tag, width, index, setNode, kick }: TagProps) {
  const [flipped, setFlipped] = useState(false);
  const verified = tag.status === "verified" && tag.payable != null;
  const nonRefundable = tag.cancellation_category === "non_refundable";
  const extra = nonRefundable ? <span className="stamp warn">Non-refundable · not comparable</span> : null;
  const gap = gapAmount(tag.listing, tag.payable);
  const pct = tag.fee_leak_pct ?? gapPct(tag.listing, tag.payable);
  const dir = () => (Math.random() > 0.5 ? 1 : -1);

  const label = `${tag.title} on ${tag.platform}, listing ${inr(tag.listing)}${verified ? `, payable ${inr(tag.payable)}` : ", not verified"}. Press to flip.`;

  return (
    <div
      className="hang"
      ref={(el) => setNode(index, el)}
      style={{ "--tw": width } as React.CSSProperties}
      onPointerEnter={(e) => {
        if (e.pointerType === "mouse") kick(index, dir() * 55);
      }}
      onPointerDown={() => kick(index, dir() * 80)}
    >
      <span className="hook" />
      <svg className="string" viewBox="0 0 100 46" preserveAspectRatio="none" aria-hidden="true">
        <path d="M50 0 L20 46 M50 0 L80 46" />
      </svg>
      <button
        type="button"
        className={`tag${tag.status !== "verified" ? " loose" : ""}${flipped ? " flipped" : ""}`}
        aria-pressed={flipped}
        aria-label={label}
        onClick={() => {
          setFlipped((f) => !f);
          kick(index, dir() * 70);
        }}
      >
        <span className="card">
          <span className="face front">
            <span className="eyelet" />
            <span className="chip">{tag.platform}</span>
            <span className="hname">{tag.title}</span>
            <span className="spacer" />
            <span className="lab">Listing price</span>
            <span className={`price${tag.listing == null ? " na" : ""}`}>{inr(tag.listing)}</span>
            {verified ? extra : <Stamp tag={tag} />}
            <span className="hint">Tap to flip</span>
          </span>
          <span className="face back">
            <span className="eyelet" />
            <span className="lab">At the payment page</span>
            {verified ? (
              <>
                <span className="price">{inr(tag.payable)}</span>
                {gap != null && (
                  <span className="delta">
                    +{inr(gap)}
                    {pct != null ? ` · +${pct}% vs listing` : " vs listing"}
                    <br />
                    observed on this run
                  </span>
                )}
                <span className="spacer" />
                <Stamp tag={tag} />
                {extra}
                <span className="hint">{cancelHint(tag.cancellation_category)}</span>
              </>
            ) : (
              <>
                <span className="price na">N/A</span>
                <span className="hint">No payable price was verified, so there is no fee gap and no score.</span>
                <span className="spacer" />
                <Stamp tag={tag} />
              </>
            )}
          </span>
        </span>
      </button>
    </div>
  );
}

interface RailProps {
  tags: TagItem[];
  /** CSS length for --tw, e.g. "clamp(190px,20vw,240px)" or "170px". */
  width: string;
  variant: "hero" | "group";
  ariaLabel?: string;
}

export function KeyTagRail({ tags, width, variant, ariaLabel }: RailProps) {
  const nodes = useRef<Array<HTMLDivElement | null>>([]);
  const swingers = useRef<Swinger[]>([]);
  const raf = useRef(0);
  const last = useRef(0);
  const reduce = useRef(false);
  const tick = useRef<(now: number) => void>(() => undefined);
  const scrollRef = useRef<HTMLDivElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  tick.current = (now: number) => {
    const dt = Math.min(0.04, (now - last.current) / 1000);
    last.current = now;
    let live = false;
    swingers.current.forEach((s, i) => {
      const acc = -SPRING * s.a - DAMPING * s.v;
      s.v += acc * dt;
      s.a += s.v * dt;
      if (s.a > MAX_ANGLE) s.a = MAX_ANGLE;
      if (s.a < -MAX_ANGLE) s.a = -MAX_ANGLE;
      if (Math.abs(s.a) < 0.02 && Math.abs(s.v) < 0.1) {
        s.a = 0;
        s.v = 0;
      } else live = true;
      const n = nodes.current[i];
      if (n) n.style.transform = `rotate(${s.a.toFixed(3)}deg)`;
    });
    raf.current = live ? requestAnimationFrame((t) => tick.current(t)) : 0;
  };

  const kick = useCallback((i: number, v: number) => {
    if (reduce.current) return;
    const s = swingers.current[i];
    if (!s) return;
    s.v += v;
    if (!raf.current) {
      last.current = performance.now();
      raf.current = requestAnimationFrame((t) => tick.current(t));
    }
  }, []);

  const setNode = useCallback((i: number, el: HTMLDivElement | null) => {
    nodes.current[i] = el;
    if (!swingers.current[i]) swingers.current[i] = { a: 0, v: 0 };
  }, []);

  useEffect(() => {
    reduce.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sc = scrollRef.current;
    if (variant === "hero" && sc && sc.scrollWidth > sc.clientWidth) sc.scrollLeft = (sc.scrollWidth - sc.clientWidth) / 2;

    const timers: number[] = [];
    let io: IntersectionObserver | null = null;
    const brush = () => {
      swingers.current.forEach((_, i) => {
        timers.push(window.setTimeout(() => kick(i, Math.max(20, 45 - i * 10)), 500 + i * 140));
      });
    };
    const box = boxRef.current;
    if (box && "IntersectionObserver" in window) {
      io = new IntersectionObserver(
        (es) => {
          if (es[0].isIntersecting) {
            io?.disconnect();
            brush();
          }
        },
        { threshold: 0.3 },
      );
      io.observe(box);
    }
    return () => {
      io?.disconnect();
      timers.forEach(clearTimeout);
      cancelAnimationFrame(raf.current);
      raf.current = 0;
    };
  }, [variant, kick]);

  const hangs = tags.map((t, i) => <HangingTag key={t.id} tag={t} width={width} index={i} setNode={setNode} kick={kick} />);

  if (variant === "hero") {
    return (
      <div className="rail-scroll" ref={scrollRef}>
        <div className="rail" aria-label={ariaLabel} ref={boxRef}>
          {hangs}
        </div>
      </div>
    );
  }
  return (
    <div className="gtags" ref={boxRef}>
      {hangs}
    </div>
  );
}
