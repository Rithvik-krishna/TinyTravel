"use client";

import React from "react";
import { glossaryFor, useGlossary } from "@/lib/extras";

/** Small "what is this?" hint next to a fee line. Renders nothing if the glossary is unavailable. */
export function GlossHint({ kind }: { kind?: string | null }) {
  const item = glossaryFor(useGlossary(), kind);
  if (!item) return null;
  return (
    <details className="gloss">
      <summary aria-label={`What is this fee? ${item.name}`}>i</summary>
      <p>
        <b>{item.name}.</b> {item.description}
      </p>
    </details>
  );
}