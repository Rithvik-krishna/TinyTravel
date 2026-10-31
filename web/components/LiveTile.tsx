const color: any = { running: "bg-brand", verified: "bg-ok", unverified: "bg-warn", blocked: "bg-bad" };
export default function LiveTile({ platform, hotel, url, status, step }: any) {
  return (
    <div className="border rounded-lg overflow-hidden border-border">
      <div className="flex justify-between items-center px-3 py-2 text-sm">
        <span><b>{platform}</b> · {hotel}</span>
        <span className={`text-brand-ink text-xs px-2 py-0.5 rounded ${color[status] || color.running}`}>{status || "running"}</span>
      </div>
      <iframe src={url} className="w-full h-40 bg-surface-2" title={`${platform}-${hotel}`} />
      <div className="px-3 py-2 text-xs text-text-muted">{step || "starting…"}</div>
    </div>
  );
}
