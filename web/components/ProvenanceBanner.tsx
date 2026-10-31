import React from "react";
import MockBadge from "./MockBadge";

export default function ProvenanceBanner({
  mock = true,
  savedLabel,
}: {
  mock?: boolean;
  savedLabel?: string | null;
}) {
  return (
    <div className="inline-flex items-center gap-2 py-1 px-3 rounded-full bg-surface-2 border border-border text-xs text-text-muted">
      <MockBadge show={mock} />
      {savedLabel && (
        <span className="font-semibold text-warning">
          SAVED RUN - {savedLabel}
        </span>
      )}
      <span className="text-[11px]">
        {mock ? "Observed probe run with guest data" : "Live run"}
      </span>
    </div>
  );
}
