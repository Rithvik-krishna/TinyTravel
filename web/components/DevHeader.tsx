"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

export function DevHeader() {
  const pathname = usePathname();
  // Replace the dev nav links on "/"
  // Product pages carry their own header; the dev links only remain on the scaffold onboarding page.
  if (pathname !== "/onboarding") {
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
