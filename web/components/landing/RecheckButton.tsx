"use client";

import React, { useState } from "react";
import { MOCK, recheck } from "@/lib/dataSource";
import { signedInr } from "@/lib/format";
import { Recheck } from "@/lib/landing";

export function RecheckButton({ offerId, platform }: { offerId: string; platform: string }) {
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  const [again, setAgain] = useState(false);

  const run = async () => {
    setBusy(true);
    setOut(MOCK ? `Re-checking the same room on ${platform}…` : `Re-checking the same room on ${platform}. This runs a full checkout again and can take 3 to 5 minutes. You can keep using the page.`);
    try {
      const r: Recheck = await recheck(offerId);
      if (r.offer_id && r.offer_id !== offerId) {
        // Never show another offer's price drift as this one's.
        setOut("A re-check is not available for this offer yet.");
        return;
      }
      const extra =
        r.delta != null && r.delta_pct != null ? ` ${signedInr(r.delta)}, ${r.delta_pct > 0 ? "+" : ""}${r.delta_pct}%.` : "";
      setOut(`${r.message ?? "Re-check finished."}${extra}`);
      setAgain(true);
    } catch {
      setOut("Re-check failed. Nothing was changed; try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="recheck-out" aria-live="polite">{out}</div>
      <button className="btn ghost sm" type="button" disabled={busy} onClick={run} style={{ justifySelf: "start" }}>
        {again ? "Re-check again" : "Re-check before paying"}
      </button>
    </>
  );
}