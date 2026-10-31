"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import demo from "@fixtures/demo_run.json";
import { startSearch } from "@/lib/dataSource";
import MockBadge from "@/components/MockBadge";

export default function Search() {
  const r = useRouter();
  const req: any = demo.search_request;
  const [text, setText] = useState(req.raw_text);
  const chips = [req.destination, `${req.check_in} → ${req.check_out}`, `${req.guests} guests`, `≤ ₹${req.budget_per_night}/night`,
    ...Object.entries(req.must_have).filter(([, v]) => v).map(([k]) => k)];
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Ask <MockBadge show /></h1>
      <textarea className="w-full border rounded p-3 bg-transparent" rows={2} value={text} onChange={e => setText(e.target.value)} />
      <div className="flex gap-2 flex-wrap">{chips.map(c => <span key={c} className="border rounded-full px-3 py-1 text-sm">{c}</span>)}</div>
      <button className="bg-blue-600 text-white rounded px-4 py-2" onClick={async () => { const { search_id } = await startSearch(text); r.push(`/investigation?id=${search_id}`); }}>Verify prices</button>
    </div>
  );
}
