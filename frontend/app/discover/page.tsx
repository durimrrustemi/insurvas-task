import { getDiscoveryRuns, getConfig } from "@/lib/api";
import { DiscoverForm } from "@/components/DiscoverForm";
import { formatDate } from "@/lib/utils";

export default async function DiscoverPage() {
  let runs: Array<Record<string, unknown>> = [];
  let countries: Array<{ code: string; name: string }> = [];

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

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-6">Discovery</h1>

      <DiscoverForm countries={countries} />

      <h2 className="text-lg font-medium mt-8 mb-3">Past runs</h2>
      {runs.length === 0 ? (
        <p className="text-sm text-gray-500">No discovery runs yet.</p>
      ) : (
        <div className="space-y-2">
          {runs.map((run) => (
            <div key={run.id as string} className="rounded border p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">{run.country as string}</span>
                <span className="text-gray-400">{formatDate(run.started_at as string)}</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Found: {run.found as number} · New: {run.new as number}
                {Array.isArray(run.queries) && ` · ${run.queries.length} queries`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
