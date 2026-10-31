"use client";

import React, { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import "@/app/landing.css";
import "@/app/flow.css";
import { Footer } from "@/components/landing/Footer";
import { useSearchId, withId } from "@/lib/flow";

const STEPS: Array<{ href: string; label: string }> = [
  { href: "/", label: "Search" },
  { href: "/investigation", label: "Investigate" },
  { href: "/compare", label: "Results" },
  { href: "/evidence", label: "Proof" },
  { href: "/verdict", label: "Verdict" },
];

function Stepper() {
  const path = usePathname();
  const { id } = useSearchId();
  // The hotel detail page sits inside the Results step.
  const current = path?.startsWith("/hotel") ? 2 : Math.max(0, STEPS.findIndex((s) => s.href === path));
  return (
    <ol className="stepper" aria-label="Progress">
      {STEPS.map((s, i) => {
        const cls = i === current ? "on" : i < current ? "past" : "";
        const inner = (
          <>
            <b>{i < current ? "✓" : i + 1}</b>
            <span className="lbl">{s.label}</span>
          </>
        );
        // Later steps only link once a search exists; the user can always go back.
        const reachable = i === 0 || id != null;
        return (
          <li key={s.href} className={cls} aria-current={i === current ? "step" : undefined}>
            {reachable ? <Link href={i === 0 ? "/" : withId(s.href, id)}>{inner}</Link> : <span className="st">{inner}</span>}
          </li>
        );
      })}
    </ol>
  );
}

export function FlowShell({ children, showSteps = true }: { children: React.ReactNode; showSteps?: boolean }) {
  return (
    <div className="tt">
      <header className="nav">
        <div className="wrap">
          <Link className="logo" href="/">
            <i />
            TinyTravel
          </Link>
          <nav aria-label="Site">
            <Link href="/#how">How it works</Link>
            <Link href="/#safety">Safety</Link>
            <Link href="/#faq">FAQ</Link>
          </nav>
          <Link className="btn sm" href="/">New search</Link>
        </div>
      </header>
      {showSteps && (
        <div className="flow-top">
          <div className="wrap">
            <Suspense fallback={null}>
              <Stepper />
            </Suspense>
          </div>
        </div>
      )}
      {children}
      <Footer platforms={[]} />
    </div>
  );
}

export function EmptyState({ title, body, href = "/", cta = "Start a search" }: { title: string; body: string; href?: string; cta?: string }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      <p className="lede">{body}</p>
      <Link className="btn" href={href}>{cta}</Link>
    </div>
  );
}

export function LoadingBlock({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-label={label} style={{ display: "grid", gap: 14 }}>
      <div className="skel" />
      <div className="skel" />
    </div>
  );
}