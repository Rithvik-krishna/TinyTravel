"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import qrcode from "qrcode-generator";
import { Handoff, isHttpUrl } from "@/lib/landing";

function CopyButton({ label, value }: { label: string; value: string }) {
  const [text, setText] = useState(`Copy ${label}`);
  const timer = useRef<number>(0);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const reset = () => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setText(`Copy ${label}`), 2200);
  };
  const click = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setText("Copied");
    } catch {
      setText(value);
    }
    reset();
  };
  return (
    <button type="button" className="btn ghost sm" onClick={click}>
      {text}
    </button>
  );
}

export function Qr({ link, png, platform }: { link: string; png?: string; platform: string }) {
  const svg = useMemo(() => {
    if (png || !link) return null;
    try {
      const q = qrcode(0, "M");
      q.addData(link);
      q.make();
      return q.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
    } catch {
      return null;
    }
  }, [link, png]);

  if (png) {
    // eslint-disable-next-line @next/next/no-img-element
    return <div className="qr"><img src={png.startsWith("data:") ? png : `data:image/png;base64,${png}`} alt={`QR code to open ${platform}`} /></div>;
  }
  if (svg) return <div className="qr" role="img" aria-label={`QR code to open ${platform}`} dangerouslySetInnerHTML={{ __html: svg }} />;
  return (
    <div className="qr">
      {isHttpUrl(link) ? <a href={link} target="_blank" rel="noopener noreferrer">Open {platform}</a> : "No link"}
    </div>
  );
}

export function HandoffPhone({ handoff, hideVerifiedTime = false }: { handoff?: Handoff | null; hideVerifiedTime?: boolean }) {
  if (!handoff) return null;
  const platform = handoff.platform ?? "the site";
  const link = handoff.deep_link ?? "";
  const cp = handoff.copy_paste ?? {};
  const fields: Array<[string, string | undefined]> = [["name", cp.name ?? cp.guest_name], ["email", cp.email], ["phone", cp.phone]];
  return (
    <div className="phone">
      <Qr link={link} png={handoff.qr_png_base64} platform={platform} />
      <div>
        <p><b style={{ color: "var(--fg)" }}>Scan to open {platform}</b></p>
        <p>You pay on the real site. We never see your password.</p>
      </div>
      {isHttpUrl(link) && (
        <a className="btn sm" href={link} target="_blank" rel="noopener noreferrer">
          Open on {platform}
        </a>
      )}
      <div className="copyrow">
        {fields.map(([k, v]) => (v ? <CopyButton key={k} label={k} value={v} /> : null))}
      </div>
      <p style={{ fontSize: 12 }}>Dummy test details.{handoff.disclaimer ? ` ${hideVerifiedTime ? handoff.disclaimer.replace(/Price verified at [^.]*\.\s*/i, "") : handoff.disclaimer}` : ""}</p>
    </div>
  );
}
