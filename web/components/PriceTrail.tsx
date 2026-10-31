import { inr } from "@/lib/dataSource";
export default function PriceTrail({ offer }: { offer: any }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="flex gap-2 flex-wrap">
        {offer.price_trail.map((p: any, i: number) => (
          <div key={i} className="border rounded px-2 py-1"><div className="text-xs text-text-muted">{p.step}</div><b>{inr(p.amount)}</b></div>
        ))}
      </div>
      {offer.fee_lines.length > 0 && (
        <table className="w-full"><tbody>
          {offer.fee_lines.map((l: any, i: number) => (<tr key={i}><td>{l.label}</td><td className="text-right">{inr(l.amount)}</td></tr>))}
          <tr className="border-t font-semibold"><td>Payable</td><td className="text-right">{inr(offer.price_final_payable)}</td></tr>
        </tbody></table>
      )}
      {offer.fee_leak_pct != null && <div className="text-xs text-text-muted">Fee leak {offer.fee_leak_pct}% (observed on this run)</div>}
    </div>
  );
}
