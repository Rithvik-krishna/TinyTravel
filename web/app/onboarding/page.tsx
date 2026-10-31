"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
const STEPS = [
  { q: "Who's travelling?", opts: ["solo", "couple", "friends", "family", "business"] },
  { q: "Budget per night?", opts: ["< ₹3k", "₹3–6k", "₹6–12k", "₹12k+"] },
  { q: "Type & rating?", opts: ["any", "budget", "business", "boutique", "luxury"] },
  { q: "Must-haves?", opts: ["breakfast", "wifi", "parking", "free cancellation"] },
  { q: "What is a good deal?", opts: ["Lowest price", "Best value", "Most transparent"] },
];
export default function Onboarding() {
  const r = useRouter(); const [i, setI] = useState(0); const [ans, setAns] = useState<string[]>([]);
  const s = STEPS[i];
  const next = (a?: string) => { const n = a ? [...ans, a] : ans; setAns(n); i + 1 >= STEPS.length ? r.push("/search") : setI(i + 1); };
  return (
    <div className="space-y-4">
      <div className="text-xs text-slate-500">Step {i + 1}/{STEPS.length}</div>
      <h1 className="text-xl font-semibold">{s.q}</h1>
      <div className="flex gap-2 flex-wrap">{s.opts.map(o => <button key={o} className="border rounded-full px-4 py-2" onClick={() => next(o)}>{o}</button>)}</div>
      <button className="text-sm text-slate-500 underline" onClick={() => r.push("/search")}>Skip</button>
    </div>
  );
}
