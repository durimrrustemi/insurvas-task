"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startDiscoveryRun } from "@/lib/api";

export function DiscoverForm({ countries }: { countries: Array<{ code: string; name: string }> }) {
  const router = useRouter();
  const [country, setCountry] = useState(countries[0]?.code || "");
  const [limit, setLimit] = useState(15);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRunning(true);
    setResult(null);
    try {
      const run = await startDiscoveryRun(country, limit);
      setResult(`Done: found ${run.found}, new ${run.new}`);
      // The page shows the results of the run in the URL.
      router.push(`/discover?run=${run.id}`);
      router.refresh();
    } catch (err) {
      setResult(`Error: ${err instanceof Error ? err.message : "unknown"}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded border p-4 space-y-3">
      <div className="flex gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-600 mb-1">Country</label>
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="rounded border px-3 py-1.5 text-sm"
          >
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name} ({c.code})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-600 mb-1">Limit</label>
          <input
            type="number"
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            min={5}
            max={100}
            className="rounded border px-3 py-1.5 text-sm w-20"
          />
        </div>
        <button
          type="submit"
          disabled={running}
          className="rounded bg-blue-500 px-4 py-1.5 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {running ? "Running..." : "Run discovery"}
        </button>
      </div>
      {running && (
        <p className="text-sm text-gray-500">
          Searching, fetching each site and scoring it. About a minute for 15 partners; progress
          shows in the API terminal.
        </p>
      )}
      {result && (
        <p className={`text-sm ${result.startsWith("Error") ? "text-red-600" : "text-green-600"}`}>
          {result}
        </p>
      )}
    </form>
  );
}
