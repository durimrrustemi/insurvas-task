import Link from "next/link";
import { getDiscoveryRuns, getConfig, getRunCandidates } from "@/lib/api";
import type { DiscoveryCandidate, DiscoveryRun } from "@/lib/types";
import { DiscoverForm } from "@/components/DiscoverForm";
import { DiscoveryResults } from "@/components/DiscoveryResults";
import { formatDate } from "@/lib/utils";

export default async function DiscoverPage({
  searchParams,
}: {
  searchParams: Promise<{ run?: string }>;
}) {
  const params = await searchParams;
  let runs: DiscoveryRun[] = [];
  let countries: Array<{ code: string; name: string }> = [];
  let candidates: DiscoveryCandidate[] = [];

  try {
    const [runsData, configData] = await Promise.all([getDiscoveryRuns(), getConfig()]);
    runs = runsData;
    countries = (configData.countries as Array<{ code: string; name: string }>) || [];
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not load data. Make sure the backend is running.</p>
      </div>
    );
  }

  // Show the run in the URL, or the latest one.
  const selected = runs.find((r) => r.id === params.run) ?? runs[0];
  if (selected) {
    candidates = await getRunCandidates(selected.id).catch(() => []);
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold mb-6">Discovery</h1>

      <DiscoverForm countries={countries} />

      {selected && (
        <section className="mt-8">
          <h2 className="text-lg font-medium mb-1">
            Results: {selected.country}, {formatDate(selected.started_at)}
          </h2>
          <p className="text-sm text-gray-500 mb-3">
            Found {selected.found} · New {selected.new} · {selected.queries.length} searches. Best
            score first; open a partner to see its evidence.
          </p>
          <DiscoveryResults candidates={candidates} />
        </section>
      )}

      <h2 className="text-lg font-medium mt-8 mb-3">Past runs</h2>
      {runs.length === 0 ? (
        <p className="text-sm text-gray-500">No discovery runs yet.</p>
      ) : (
        <div className="space-y-2">
          {runs.map((run) => (
            <Link
              key={run.id}
              href={`/discover?run=${run.id}`}
              className={`block rounded border p-3 text-sm hover:bg-gray-50 ${
                run.id === selected?.id ? "border-blue-400 bg-blue-50" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{run.country}</span>
                <span className="text-gray-400">{formatDate(run.started_at)}</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Found: {run.found} · New: {run.new} · {run.queries.length} queries
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
