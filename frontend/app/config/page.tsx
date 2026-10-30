import { getConfig } from "@/lib/api";

export default async function ConfigPage() {
  let config: Record<string, unknown>;
  try {
    config = await getConfig();
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not load config. Make sure the backend is running.</p>
      </div>
    );
  }

  const countries = config.countries as Array<Record<string, unknown>>;
  const weights = config.criterion_weights as Record<string, number>;
  const signals = config.signals as Record<
    string,
    Record<string, { weight: number; description: string }>
  >;
  const gates = config.gates as Record<string, { description: string; required_before: string }>;
  const cadence = config.cadence as Record<string, unknown> | null;

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-semibold mb-2">Configuration</h1>
      <p className="text-sm text-gray-500 mb-6">
        Read-only view. Change values in{" "}
        <code className="bg-gray-100 px-1 rounded">config/*.yaml</code> and restart.
      </p>

      {/* Criterion weights */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-2">Criterion Weights</h2>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(weights).map(([key, val]) => (
            <div key={key} className="flex justify-between rounded border px-3 py-2">
              <span className="capitalize">{key}</span>
              <span className="font-medium">{val}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Signals */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-2">Signals</h2>
        {Object.entries(signals).map(([criterion, sigs]) => (
          <div key={criterion} className="mb-3">
            <h3 className="text-sm font-medium text-gray-600 capitalize mb-1">{criterion}</h3>
            <div className="space-y-1">
              {Object.entries(sigs).map(([key, sig]) => (
                <div key={key} className="flex items-center text-xs rounded border px-3 py-1.5">
                  <span className="flex-1">{key.replace(/_/g, " ")}</span>
                  <span className="text-gray-500 mr-4">{sig.description}</span>
                  <span className="font-medium">wt: {sig.weight}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      {/* Gates */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-2">Gates</h2>
        <div className="space-y-2">
          {Object.entries(gates).map(([name, gate]) => (
            <div key={name} className="rounded border px-3 py-2 text-sm">
              <span className="font-medium">{name.replace(/_/g, " ")}</span>
              <span className="text-gray-500 ml-2">— {gate.description}</span>
              <span className="text-xs text-gray-400 ml-2">
                (required before {gate.required_before.replace(/_/g, " ")})
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Countries */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-2">Countries ({countries.length})</h2>
        <div className="grid grid-cols-2 gap-2">
          {countries.map((c) => (
            <div key={c.code as string} className="rounded border px-3 py-2 text-sm">
              <span className="font-medium">{c.name as string}</span>
              <span className="text-gray-500 ml-1">({c.code as string})</span>
              <div className="text-xs text-gray-400 mt-0.5">
                English: {c.english_baseline as number} · {c.timezone as string}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Cadence */}
      {cadence && (
        <section className="mb-8">
          <h2 className="text-lg font-medium mb-2">Cadence</h2>
          <div className="text-sm space-y-1">
            <div>Follow-up days: {(cadence.follow_up_days as number[]).join(", ")}</div>
            <div>Reminder: {cadence.reminder_days as number} days</div>
            <div>Stale stage: {cadence.stale_stage_days as number} days</div>
            <div>Max follow-ups: {cadence.max_follow_ups as number}</div>
          </div>
        </section>
      )}
    </div>
  );
}
