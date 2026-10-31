export default function MockBadge({ show }: { show: boolean }) {
  if (!show) return null;
  return <span className="text-xs px-2 py-0.5 rounded bg-warn-soft text-warn font-semibold">MOCK DATA</span>;
}
