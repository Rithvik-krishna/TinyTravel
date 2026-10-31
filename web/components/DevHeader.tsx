"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function DevHeader() {
  const pathname = usePathname();
  // Replace the dev nav links on "/"
  if (pathname === "/") {
    return null;
  }

  return (
    <header className="border-b border-border px-4 py-3 flex gap-4 text-sm items-center bg-surface">
      <Link href="/" className="font-semibold text-brand">
        TinyTravel
      </Link>
      {["onboarding", "search", "investigation", "compare", "evidence", "verdict"].map((p) => (
        <Link
          key={p}
          href={`/${p}`}
          className="text-text-muted hover:text-text hover:underline capitalize"
        >
          {p}
        </Link>
      ))}
    </header>
  );
}
