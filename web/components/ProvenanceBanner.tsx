import React from "react";
import MockBadge from "./MockBadge";

export function ProvenanceBanner({
  mock = true,
  savedLabel,
}: {
  mock?: boolean;
  savedLabel?: string | null;
}) {
  return (
    <div className="inline-flex flex-wrap items-center justify-center gap-1.5 sm:gap-2 py-1 px-3 rounded-full bg-surface-2 border border-border text-[11px] sm:text-xs text-text-muted text-center max-w-[95vw]">
      <MockBadge show={mock} />
      {savedLabel && (
        <span className="font-semibold text-warning">
          SAVED RUN - {savedLabel}
        </span>
      )}
      <span className="text-[10px] sm:text-[11px] hidden min-[480px]:inline">
        {mock ? "Observed probe run with guest data" : "Live run"}
      </span>
    </div>
  );
}

export default ProvenanceBanner;
