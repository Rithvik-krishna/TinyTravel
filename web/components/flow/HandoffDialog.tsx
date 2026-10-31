"use client";

import React, { useEffect, useRef, useState } from "react";
import { TagItem } from "@/lib/tags";
import { inr, shortTime } from "@/lib/format";
import { Handoff, isHttpUrl } from "@/lib/landing";
import { Qr } from "@/components/landing/HandoffPhone";
import { RecheckButton } from "@/components/landing/RecheckButton";

interface Props {
  open: boolean;
  onClose: () => void;
  offer: TagItem;
  hotelName: string;
  stay: string;
  handoff?: Handoff | null;
}

export function HandoffDialog({ open, onClose, offer, hotelName, stay, handoff }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [copied, setCopied] = useState("Copy selection");

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  // Only trust a handoff that belongs to this exact offer.
  const own = handoff && handoff.offer_id === offer.id ? handoff : null;
  const link = own && isHttpUrl(own.deep_link) ? own.deep_link : isHttpUrl(offer.hotel_url) ? offer.hotel_url : "";
  const at = shortTime(offer.verifiedAt);

  const copy = async () => {
    const t = `${hotelName} · ${offer.room_type ?? ""} · ${offer.meal_plan ?? ""} · ${offer.cancellation_policy ?? ""} · ${stay} · expect to pay ${inr(offer.payable, offer.currency)} on ${offer.platform}${at ? ` (verified ${at})` : ""}`;
    try {
      await navigator.clipboard.writeText(t);
      setCopied("Copied");
    } catch {
      setCopied("Select and copy from the page");
    }
    window.setTimeout(() => setCopied("Copy selection"), 2200);
  };

  return (
    <dialog ref={ref} aria-labelledby="ho-t" onClose={onClose} onClick={(e) => e.target === ref.current && ref.current?.close()}>
      <div className="dlg">
        <button className="btn ghost sm" type="button" style={{ justifySelf: "end" }} onClick={() => ref.current?.close()}>Close</button>
        <h3 id="ho-t" style={{ fontSize: 26 }}>Finish on {offer.platform}</h3>
        <div className="sumcard">
          <dl>
            <dt>Hotel</dt><dd>{hotelName}</dd>
            {offer.room_type && (<><dt>Room</dt><dd>{offer.room_type}</dd></>)}
            {offer.meal_plan && (<><dt>Meals</dt><dd>{offer.meal_plan}</dd></>)}
            {offer.cancellation_policy && (<><dt>Cancellation</dt><dd>{offer.cancellation_policy}</dd></>)}
            {stay && (<><dt>Stay</dt><dd>{stay}</dd></>)}
            <dt>Expect to pay</dt><dd><b className="num">{inr(offer.payable, offer.currency)}</b></dd>
          </dl>
        </div>
        <ol className="todo">
          <li><div><b>Open {offer.platform}</b><br /><span className="muted">The link opens the property on {offer.platform}. Pick exactly the room above. The total should match.</span></div></li>
          <li><div><b>Use your own details</b><br /><span className="muted">TinyTravel never sees your name, card or password.</span></div></li>
          <li><div><b>Pay on {offer.platform}</b><br /><span className="muted">Nothing is booked until you pay there.</span></div></li>
        </ol>
        {link ? (
          <a className="btn" style={{ width: "100%" }} href={link} target="_blank" rel="noopener noreferrer">Open {offer.platform}</a>
        ) : (
          <p className="notice warn">No link is available for this offer.</p>
        )}
        {link && (
          <div className="qrbox">
            <div style={{ width: 132 }}><Qr link={link} png={own?.qr_png_base64} platform={offer.platform} /></div>
            <div className="fine">Scan to open it on your phone.<br />{at ? `Verified ${at}. ` : ""}Prices can change.</div>
          </div>
        )}
        {own?.copy_paste && <p className="fine">Dummy test details used by our agents: {own.copy_paste.name}. Use your own on the real site.</p>}
        <div style={{ display: "grid", gap: 8 }}>
          <RecheckButton offerId={offer.id} platform={offer.platform} />
          <button className="btn ghost sm" type="button" style={{ justifySelf: "start" }} onClick={copy}>{copied}</button>
        </div>
      </div>
    </dialog>
  );
}