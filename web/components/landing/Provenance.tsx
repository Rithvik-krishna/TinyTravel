import React from "react";
import { LandingMeta, provenanceOf } from "@/lib/landing";

/** MOCK DATA when _meta.mock, SAVED RUN - <label> for saved runs, nothing when live. */
export function Provenance({ meta }: { meta?: LandingMeta }) {
  const p = provenanceOf(meta);
  if (!p.mock && !p.savedLabel) return null;
  return (
    <>
      {p.mock && <span className="badge mock">{p.label || "Mock data"}</span>}
      {p.savedLabel && <span className="badge warn">SAVED RUN - {p.savedLabel}</span>}
    </>
  );
}