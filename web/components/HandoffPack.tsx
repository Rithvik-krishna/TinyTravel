"use client";
import { QRCodeSVG } from "qrcode.react";
import { inr } from "@/lib/dataSource";
export default function HandoffPack({ pack, onRecheck, recheckResult }: any) {
  const c = pack.selection_card;
  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex gap-4 items-start">
        <QRCodeSVG value={pack.deep_link} size={112} />
        <div className="text-sm space-y-1">
          <div className="font-semibold">{c.hotel} · {pack.platform}</div>
          <div>{c.room_type} · {c.meal_plan}</div>
          <div>{c.cancellation}</div>
          <div>{c.dates} · {c.guests} guests</div>
          <div className="font-semibold">Expect to pay {inr(c.expected_final_payable)}</div>
          <a className="text-brand underline" href={pack.deep_link} target="_blank">Open on {pack.platform}</a>
        </div>
      </div>
      <div className="text-xs bg-surface-2 rounded p-2">
        Copy-paste: {pack.copy_paste.name} · {pack.copy_paste.email} · {pack.copy_paste.phone}
      </div>
      <div className="text-xs text-text-muted">{pack.disclaimer}</div>
      <button className="border rounded px-3 py-1 text-sm" onClick={onRecheck}>Re-check before paying</button>
      {recheckResult && <div className="text-sm">{recheckResult.message}</div>}
    </div>
  );
}
