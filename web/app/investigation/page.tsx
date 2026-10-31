"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { openStream, MOCK } from "@/lib/dataSource";
import LiveTile from "@/components/LiveTile";
import MockBadge from "@/components/MockBadge";

function Inner() {
  const id = useSearchParams().get("id") || "mock_search";
  const r = useRouter();
  const [tiles, setTiles] = useState<Record<string, any>>({});
  const [count, setCount] = useState<any>({});
  const [done, setDone] = useState(false);
  useEffect(() => openStream(id, (e, d) => {
    if (e === "listings_found") setCount((c: any) => ({ ...c, listings: d.count }));
    if (e === "hotels_grouped") setCount((c: any) => ({ ...c, hotels: d.hotel_groups.length }));
    if (e === "agent_started") setTiles(t => ({ ...t, [d.run_id]: { ...d, status: "running" } }));
    if (e === "agent_progress") setTiles(t => ({ ...t, [d.run_id]: { ...t[d.run_id], step: d.step_text } }));
    if (e === "agent_done") setTiles(t => ({ ...t, [d.run_id]: { ...t[d.run_id], status: d.status } }));
    if (e === "ranking_ready") setDone(true);
  }, 1), [id]);
  const all = Object.values(tiles);
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Investigation <MockBadge show={MOCK} /></h1>
      <p className="text-sm text-slate-500">Checking sites like a real buyer. ~3–5 min.</p>
      <div className="text-sm flex gap-4"><span>Listings: {count.listings ?? "…"}</span><span>Hotels: {count.hotels ?? "…"}</span>
        <span>Verified: {all.filter((t: any) => t.status === "verified").length}</span>
        <span>Blocked: {all.filter((t: any) => t.status === "blocked").length}</span></div>
      <div className="grid md:grid-cols-3 gap-3">
        {all.map((t: any) => <LiveTile key={t.run_id} platform={t.platform} hotel={t.hotel} url={t.streaming_url} status={t.status} step={t.step} />)}
      </div>
      {done && <button className="bg-blue-600 text-white rounded px-4 py-2" onClick={() => r.push("/verdict")}>See verdict</button>}
    </div>
  );
}
export default function Page() { return <Suspense><Inner /></Suspense>; }
