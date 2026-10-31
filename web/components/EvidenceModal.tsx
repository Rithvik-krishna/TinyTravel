"use client";
export default function EvidenceModal({ evidence, onClose }: { evidence: any; onClose: () => void }) {
  if (!evidence) return null;
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white dark:bg-slate-900 rounded-lg p-4 max-w-lg w-full space-y-2" onClick={e => e.stopPropagation()}>
        <img src={evidence.url} alt="evidence" className="w-full rounded border" />
        <div className="text-xs text-slate-500">{evidence.type} · step: {evidence.step} · {evidence.captured_at} · value: {evidence.extracted_value} {evidence.currency}</div>
        <button className="border rounded px-3 py-1 text-sm" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}
