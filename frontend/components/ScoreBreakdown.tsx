"use client";

import { useState } from "react";
import type { Partner, Signal } from "@/lib/types";
import { ScoreBar } from "./ScoreBar";
import { useRouter } from "next/navigation";
import { scorePartner } from "@/lib/api";

const CRITERIA = [
  { key: "english", label: "English", field: "score_english" as const },
  { key: "insurance", label: "Insurance", field: "score_insurance" as const },
  { key: "size", label: "Size", field: "score_size" as const },
  { key: "compliance", label: "Compliance", field: "score_compliance" as const },
];

export function ScoreBreakdown({ partner, signals }: { partner: Partner; signals: Signal[] }) {
  const router = useRouter();
  const [scoring, setScoring] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const grouped: Record<string, Signal[]> = {};
  for (const s of signals) {
    (grouped[s.criterion] ??= []).push(s);
  }

  async function handleScore() {
    setScoring(true);
    setError(null);
    try {
      await scorePartner(partner.id);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setScoring(false);
    }
  }

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium">Score breakdown</h2>
        <button
          onClick={handleScore}
          disabled={scoring}
          className="rounded bg-blue-500 px-3 py-1 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {scoring ? "Scoring..." : "Re-score"}
        </button>
      </div>

      {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="mb-4">
        <ScoreBar score={partner.score_total} label="Total" />
      </div>

      <div className="space-y-2">
        {CRITERIA.map(({ key, label, field }) => {
          const criterionSignals = grouped[key] || [];
          const isExpanded = expanded === key;
          const score = partner[field];

          return (
            <div key={key} className="rounded border">
              <button
                className="flex w-full items-center gap-2 p-3 text-left hover:bg-gray-50"
                onClick={() => setExpanded(isExpanded ? null : key)}
              >
                <ScoreBar score={score} label={label} />
                <span className="ml-auto text-xs text-gray-400">
                  {criterionSignals.length} signal{criterionSignals.length !== 1 ? "s" : ""}
                  {isExpanded ? " ▲" : " ▼"}
                </span>
              </button>

              {isExpanded && (
                <div className="border-t px-3 pb-3">
                  {criterionSignals.length === 0 ? (
                    <p className="text-sm text-gray-400 pt-2">No signals — shown as gap</p>
                  ) : (
                    <div className="space-y-2 pt-2">
                      {criterionSignals.map((s) => (
                        <div key={s.id} className="text-sm">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{s.key.replace(/_/g, " ")}</span>
                            <span className="ml-auto text-xs text-gray-500">
                              val: {s.value.toFixed(2)} · wt: {s.weight.toFixed(1)}
                            </span>
                          </div>
                          {s.matched_text && (
                            <p className="text-xs text-gray-600 mt-0.5">{s.matched_text}</p>
                          )}
                          {s.source_url && (
                            <a
                              href={s.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-500 hover:underline"
                            >
                              {s.source_url}
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
