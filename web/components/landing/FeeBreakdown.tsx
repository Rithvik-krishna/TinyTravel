import React from "react";
import { FeeLine, TagItem } from "@/lib/tags";
import { inr } from "@/lib/format";
import { groupFeeLines } from "@/lib/landing";

const amount = (n: number, currency: string) => (n < 0 ? `−${inr(Math.abs(n), currency)}` : inr(n, currency));

function Group({ title, lines, currency }: { title: string; lines: FeeLine[]; currency: string }) {
  if (lines.length === 0) return null;
  return (
    <>
      <tr className="grp"><td colSpan={2}>{title}</td></tr>
      {lines.map((l, i) => (
        <tr key={`${l.label}-${i}`}>
          <td>{l.label}</td>
          <td>{amount(l.amount, currency)}</td>
        </tr>
      ))}
    </>
  );
}

export function FeeBreakdown({ offer }: { offer: TagItem }) {
  const g = groupFeeLines(offer.fee_lines);
  const c = offer.currency;
  return (
    <div className="fees">
      <h3>Fee breakdown</h3>
      <table aria-label="Fee breakdown">
        <tbody>
          <Group title="Room" lines={g.room} currency={c} />
          <Group title="Discounts" lines={g.discounts} currency={c} />
          <Group title="Taxes" lines={g.taxes} currency={c} />
          <Group title="Platform fees" lines={g.platform} currency={c} />
          <Group title="Other" lines={g.other} currency={c} />
          <tr className="tot">
            <td>Total at payment</td>
            <td>{inr(offer.payable, c)}</td>
          </tr>
        </tbody>
      </table>
      {offer.reconciliation === "ok" && offer.payable != null && <p className="ok">✓ The lines add up to {inr(offer.payable, c)}</p>}
      {offer.reconciliation === "mismatch" && <p className="small">The lines don&apos;t add up to the total, so we show the price as observed.</p>}
      <p className="small">Taxes are shown apart from platform fees.</p>
    </div>
  );
}