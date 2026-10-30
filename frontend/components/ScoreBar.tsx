export function ScoreBar({ score, label }: { score: number | null; label: string }) {
  if (score === null) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <span className="w-24 text-gray-500">{label}</span>
        <span className="text-gray-400">unknown</span>
      </div>
    );
  }
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2 text-sm">
      <span className="w-24 text-gray-500">{label}</span>
      <div className="h-2 w-32 rounded-full bg-gray-200">
        <div
          className="h-2 rounded-full bg-blue-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-gray-700">{pct}%</span>
    </div>
  );
}
