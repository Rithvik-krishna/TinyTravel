import React from "react";
import Link from "next/link";

export function Footer() {
  const platforms = [
    { name: "Cleartrip", status: "Live" },
    { name: "Agoda", status: "Live" },
    { name: "Booking.com", status: "Live" },
    { name: "MakeMyTrip", status: "Coming soon" },
  ];

  return (
    <footer className="w-full border-t border-border bg-surface-2/60 py-12 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-brand text-white font-black text-xs">
                TT
              </span>
              <span className="font-extrabold text-lg text-text">
                Tiny<span className="text-brand">Travel</span>
              </span>
            </div>
            <p className="text-xs sm:text-sm text-text-muted">
              The price you see isn&apos;t the price you pay.
            </p>
          </div>

          <div className="rounded-2xl bg-surface border border-border p-3.5 flex flex-col sm:flex-row items-start sm:items-center gap-3 text-xs">
            <span className="font-semibold text-text">Platforms checked:</span>
            <div className="flex flex-wrap items-center gap-2">
              {platforms.map((p) => (
                <span
                  key={p.name}
                  className="inline-flex items-center gap-1 rounded-full bg-surface-2 border border-border/80 px-2.5 py-0.5 text-[11px] text-text-muted"
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      p.status === "Live" ? "bg-success" : "bg-text-muted"
                    }`}
                  />
                  <strong className="font-medium text-text">{p.name}</strong>
                  <span className="text-[10px]">({p.status})</span>
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-6 border-t border-border/70 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-text-muted">
          <div>
            <span>Built at Swim with TinyFish, Bangalore.</span>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <a
              href="https://github.com/Rithvik-krishna/TinyTravel"
              target="_blank"
              rel="noreferrer"
              className="hover:text-text transition-colors"
            >
              GitHub Repo
            </a>
            <a href="#how-it-works" className="hover:text-text transition-colors">
              Documentation
            </a>
            <a href="#safety" className="hover:text-text transition-colors">
              Safety Guardrails
            </a>
            <a href="#faq" className="hover:text-text transition-colors">
              FAQ
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
