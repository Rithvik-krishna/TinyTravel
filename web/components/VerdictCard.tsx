export default function VerdictCard({ title, headline, offerId, onSelect }: any) {
  return (
    <button onClick={() => onSelect?.(offerId)} className="text-left border rounded-lg p-4 hover:border-brand w-full">
      <div className="text-xs uppercase text-text-muted">{title}</div>
      <div className="font-medium mt-1">{headline}</div>
    </button>
  );
}
