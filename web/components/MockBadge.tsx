export default function MockBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return <span className="text-xs px-2 py-0.5 rounded bg-amber-200 text-amber-900 font-semibold">MOCK DATA</span>;
}
