"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";

interface NavLink {
  href: string;
  label: string;
}

/** Full-width glass nav: big logo, centred links, prominent white CTA. On small screens the links move into a glass sheet. */
export function NavPill({
  links,
  ctaLabel,
  ctaHref,
  logoHref = "/",
}: {
  links: NavLink[];
  ctaLabel: string;
  ctaHref: string;
  logoHref?: string;
}) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header className="nav">
      <div className="wrap">
        <div className="navpill">
          <Link className="logo" href={logoHref}>
            <i />
            TinyTravel
          </Link>
          <nav className="navlinks" aria-label="Sections">
            {links.map((l) => (
              <Link key={l.href} href={l.href}>
                {l.label}
              </Link>
            ))}
          </nav>
          <div className="nav-actions">
            <Link className="btn navcta" href={ctaHref}>
              {ctaLabel}
            </Link>
            <button
              className="menubtn"
              type="button"
              aria-label="Menu"
              aria-expanded={open}
              aria-controls="navsheet"
              onClick={() => setOpen((o) => !o)}
            >
              <span aria-hidden="true">{open ? "✕" : "☰"}</span>
            </button>
          </div>
        </div>
        {open && (
          <div className="navsheet" id="navsheet">
            {links.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)}>
                {l.label}
              </Link>
            ))}
            <Link className="btn" href={ctaHref} onClick={() => setOpen(false)}>
              {ctaLabel}
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
