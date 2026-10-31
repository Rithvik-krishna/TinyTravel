"use client";

import React, { useState } from "react";
import { MOCK } from "@/lib/dataSource";
import { reportUrl } from "@/lib/extras";

/** Printable evidence report served by the API. Not offered when there is no live API behind the page. */
export function ReportLink({ searchId }: { searchId: string | null }) {
  const [label, setLabel] = useState("Copy link");
  if (MOCK || !searchId) return null;
  const url = reportUrl(searchId);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setLabel("Copied");
    } catch {
      setLabel(url);
    }
    window.setTimeout(() => setLabel("Copy link"), 2200);
  };
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
      <a className="btn ghost sm" href={url} target="_blank" rel="noopener noreferrer">Open evidence report</a>
      <button className="btn ghost sm" type="button" onClick={copy}>{label}</button>
    </div>
  );
}