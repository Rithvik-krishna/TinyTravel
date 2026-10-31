const color: any = { running: "bg-blue-500", verified: "bg-green-600", unverified: "bg-amber-500", blocked: "bg-red-600" };
export default function LiveTile({ platform, hotel, url, status, step }: any) {
  return (
    <div className="border rounded-lg overflow-hidden border-slate-200 dark:border-slate-800">
      <div className="flex justify-between items-center px-3 py-2 text-sm">
        <span><b>{platform}</b> · {hotel}</span>
        <span className={`text-white text-xs px-2 py-0.5 rounded ${color[status] || color.running}`}>{status || "running"}</span>
      </div>
      <iframe src={url} className="w-full h-40 bg-slate-100 dark:bg-slate-900" title={`${platform}-${hotel}`} />
      <div className="px-3 py-2 text-xs text-slate-500">{step || "starting…"}</div>
    </div>
  );
}
