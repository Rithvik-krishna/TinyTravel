"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Menu, X, ShieldCheck } from "lucide-react";

interface NavBarProps {
  isMock?: boolean;
}

export function NavBar({ isMock = true }: NavBarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "How it works", href: "#how-it-works" },
    { label: "Live probes", href: "#watch-it-verify" },
    { label: "Proof & Trail", href: "#proof" },
    { label: "Safety & Privacy", href: "#safety" },
    { label: "FAQ", href: "#faq" },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-border/80 bg-surface/90 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2.5 font-extrabold text-lg sm:text-xl tracking-tight text-text hover:opacity-90 transition-opacity"
        >
          <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-brand text-white shadow-sm font-black text-sm">
            TT
          </span>
          <span className="text-text">
            Tiny<span className="text-brand">Travel</span>
          </span>
          {isMock && (
            <span className="hidden sm:inline-flex items-center gap-1 rounded-full bg-warning/10 border border-warning/30 px-2 py-0.5 text-[10px] font-semibold text-warning tracking-wide uppercase">
              Demo Run
            </span>
          )}
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-7 text-sm font-medium text-text-muted">
          {navLinks.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="transition-colors hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded-md px-1 py-0.5"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Right CTA + Mobile Toggle */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <Link
            href="/search"
            className="inline-flex items-center justify-center rounded-full bg-brand px-3.5 py-1.5 sm:px-5 sm:py-2 text-xs sm:text-sm font-semibold text-white shadow-sm transition-all hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand active:scale-[0.98] whitespace-nowrap"
          >
            Verify prices
          </Link>

          <button
            type="button"
            className="md:hidden inline-flex items-center justify-center p-1.5 sm:p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            onClick={() => setMobileMenuOpen((prev) => !prev)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-border bg-surface px-4 py-4 space-y-3 shadow-lg">
          <div className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <a
                key={link.href}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2 rounded-lg text-sm font-medium text-text-muted hover:text-text hover:bg-surface-2 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
          <div className="pt-2 border-t border-border">
            <Link
              href="/search"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center rounded-lg bg-brand py-2.5 text-sm font-semibold text-white shadow-sm"
            >
              Verify prices
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
