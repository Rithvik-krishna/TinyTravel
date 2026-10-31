"use client";
import { useState } from "react";
import demo from "@fixtures/demo_run.json";
import { getHandoff, recheck } from "@/lib/dataSource";
import VerdictCard from "@/components/VerdictCard";
import HandoffPack from "@/components/HandoffPack";
import MockBadge from "@/components/MockBadge";
export default function Verdict() {
  const d: any = demo; const v = d.verdicts.per_hotel[d.verdicts.hero_hotel_id];
  const [pack, setPack] = useState<any>(null); const [rc, setRc] = useState<any>(null); const [sel, setSel] = useState("");
  const pick = async (id: string) => { setSel(id); setRc(null); setPack(await getHandoff(id)); };
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Verdict <MockBadge show /></h1>
      <div className="grid md:grid-cols-3 gap-3">
        <VerdictCard title="Cheapest verified" headline={v.headlines.cheapest_verified} offerId={v.cheapest_verified} onSelect={pick} />
        <VerdictCard title="Safe-cheapest (free cancellation)" headline={v.headlines.safe_cheapest} offerId={v.safe_cheapest} onSelect={pick} />
        <VerdictCard title="Best for you" headline={v.headlines.best_for_you} offerId={v.best_for_you} onSelect={pick} />
      </div>
      {pack && <HandoffPack pack={pack} onRecheck={async () => setRc(await recheck(sel))} recheckResult={rc} />}
    </div>
  );
}
