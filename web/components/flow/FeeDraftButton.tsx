"use client";

import React, { useEffect, useRef, useState } from "react";
import { fetchFeeDraft, FeeDraft } from "@/lib/extras";

/** Opens a factual draft question about the fees, written by the backend. Hidden if no draft can be loaded. */
export function FeeDraftButton({ offerId }: { offerId: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState<FeeDraft | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "failed">("idle");
  const [text, setText] = useState("");
  const [copied, setCopied] = useState("Copy message");

  useEffect(() => {
    setDraft(null);
    setState("idle");
  }, [offerId]);

  const open = async () => {
    setState("loading");
    const d = await fetchFeeDraft(offerId);
    if (!d) {
      setState("failed");
      return;
    }
    setDraft(d);
    setText(d.draft_message);
    setState("idle");
    ref.current?.showModal();
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied("Copied");
    } catch {
      setCopied("Select and copy the text");
    }
    window.setTimeout(() => setCopied("Copy message"), 2200);
  };

  return (
    <>
      <button className="btn ghost sm" type="button" onClick={open} disabled={state === "loading"}>
        {state === "loading" ? "Preparing…" : "Ask about these fees"}
      </button>
      {state === "failed" && <span className="fine" role="status"> A draft is not available for this offer.</span>}
      <dialog ref={ref} aria-labelledby="fd-t" onClick={(e) => e.target === ref.current && ref.current?.close()}>
        <div className="dlg">
          <h3 id="fd-t">{draft?.subject ?? "Ask about these fees"}</h3>
          <textarea aria-label="Message" value={text} onChange={(e) => setText(e.target.value)} rows={9} className="draft" />
          <p className="fine">A factual draft based on what we observed. Edit it before you send it anywhere.</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn sm" type="button" onClick={copy}>{copied}</button>
            <button className="btn ghost sm" type="button" onClick={() => ref.current?.close()}>Close</button>
          </div>
        </div>
      </dialog>
    </>
  );
}