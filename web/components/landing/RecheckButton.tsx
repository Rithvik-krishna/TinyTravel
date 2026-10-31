"use client";

import React, { useState } from "react";
import { recheck } from "@/lib/dataSource";
import { signedInr } from "@/lib/format";
import { Recheck } from "@/lib/landing";

export function RecheckButton({ offerId, platform }: { offerId: string; platform: string }) {
  const [out, setOut] = useState("");
  const [busy, setBusy] = useState(false);
  const [again, setAgain] = useState(false);

  const run = async () => {
    setBusy(true);
    setOut(`Re-checking the same room on ${platform}…`);
    try {
      const r: Recheck = await recheck(offerId);
      if (r.offer_id && r.offer_id !== offerId) {
        // The demo only ships a saved re-check for one offer; never show another offer's drift as this one's.
        setOut("No saved re-check exists for this offer in the demo. A live re-check would run the same steps again.");
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