import React from "react";
import { FeeLine, TagItem } from "@/lib/tags";
import { inr } from "@/lib/format";
import { groupFeeLines } from "@/lib/landing";

const amount = (n: number) => (n < 0 ? `−${inr(Math.abs(n))}` : inr(n));

function Group({ title, lines }: { title: string; lines: FeeLine[] }) {
  if (lines.length === 0) return null;
  return (
    <>
      <tr className="grp"><td colSpan={2}>{title}</td></tr>
      {lines.map((l, i) => (
        <tr key={`${l.label}-${i}`}>
          <td>{l.label}</td>
          <td>{amount(l.amount)}</td>
        </tr>
      ))}
    </>
  );
}

export function FeeBreakdown({ offer }: { offer: TagItem }) {
  const g = groupFeeLines(offer.fee_lines);
  return (
    <div className="fees">
      <h3>Fee breakdown</h3>
      <table aria-label="Fee breakdown">
        <tbody>
          <Group title="Room" lines={g.room} />
          <Group title="Discounts" lines={g.discounts} />
          <Group title="Taxes" lines={g.taxes} />
          <Group title="Platform fees" lines={g.platform} />
          <Group title="Other" lines={g.other} />
          <tr className="tot">
            <td>Payable</td>
            <td>{inr(offer.payable)}</td>
          </tr>
        </tbody>
      </table>
      {offer.reconciliation === "ok" && offer.payable != null && <p className="ok">✓ Lines add up to {inr(offer.payable)}</p>}
      {offer.reconciliation === "mismatch" && <p className="small">The fee lines do not add up to the payable price, so this breakdown is not confirmed.</p>}
      <p className="small">Taxes are shown apart from platform fees.{offer.notes ? ` ${offer.notes}` : ""}</p>
    </div>
  );
}