import React from "react";
import { LandingMeta, provenanceOf } from "@/lib/landing";

/** MOCK DATA when _meta.mock, SAVED RUN - <label> for saved runs, nothing when live. */
export function Provenance({ meta }: { meta?: LandingMeta }) {
  // Internal provenance badges (mock / saved run) are off for users; set NEXT_PUBLIC_SHOW_PROVENANCE=1 to show them.
  if (process.env.NEXT_PUBLIC_SHOW_PROVENANCE !== "1") return null;
  const p = provenanceOf(meta);
  if (!p.mock && !p.savedLabel) return null;
  return (
    <>
      {p.mock && <span className="badge mock">{p.label || "Mock data"}</span>}
      {p.savedLabel && <span className="badge warn">SAVED RUN - {p.savedLabel}</span>}
    </>
  );
}