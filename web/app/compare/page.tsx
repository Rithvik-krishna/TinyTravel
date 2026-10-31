import demo from "@fixtures/demo_run.json";
import { inr } from "@/lib/dataSource";
import MockBadge from "@/components/MockBadge";
export default function Compare() {
  const d: any = demo;
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold">Hotel comparison <MockBadge show /></h1>
      {d.verdicts.non_comparable_warnings.map((w: any) => <div key={w.offer_id} className="text-sm bg-amber-100 text-amber-900 rounded p-2">{w.message}</div>)}
      {d.hotel_groups.map((g: any) => (
        <div key={g.hotel_id} className="border rounded-lg p-4 space-y-2">
          <div className="font-semibold">{g.canonical_name} <span className="text-xs text-slate-500">({g.area})</span></div>
          <div className="text-xs text-slate-500">{g.match_status} · {Math.round(g.confidence * 100)}% · {g.why}</div>
          <table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th>Site</th><th>Status</th><th>Listing</th><th>Payable</th><th>Leak</th><th>Cancel</th></tr></thead><tbody>
            {g.offer_ids.map((id: string) => { const o = d.offers.find((x: any) => x.offer_id === id); return (
              <tr key={id}><td>{o.site}</td><td>{o.status}{o.blocker ? ` (${o.blocker})` : ""}</td><td>{inr(o.price_shown_on_listing)}</td><td>{inr(o.price_final_payable)}</td><td>{o.fee_leak_pct ?? "N/A"}{o.fee_leak_pct != null && "%"}</td><td>{o.cancellation_category ?? "N/A"}</td></tr>); })}
          </tbody></table>
        </div>
      ))}
    </div>
  );
}
