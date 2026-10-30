"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Partner } from "@/lib/types";
import { transitionStage } from "@/lib/api";
import { stageColor, formatScore } from "@/lib/utils";
import Link from "next/link";

const STAGE_LABELS: Record<string, string> = {
  found: "Found",
  contacted: "Contacted",
  replied: "Replied",
  in_talks: "In Talks",
  test_calls: "Test Calls",
  signed: "Signed",
  lost: "Lost",
};

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  found: ["contacted", "lost"],
  contacted: ["replied", "lost"],
  replied: ["in_talks", "lost"],
  in_talks: ["test_calls", "lost"],
  test_calls: ["signed", "lost"],
  signed: ["lost"],
  lost: ["found"],
};

export function KanbanBoard({
  columns,
  stages,
}: {
  columns: Record<string, Partner[]>;
  stages: string[];
}) {
  const router = useRouter();
  const [moving, setMoving] = useState<string | null>(null);

  async function handleMove(partnerId: string, toStage: string) {
    setMoving(partnerId);
    try {
      await transitionStage(partnerId, toStage);
      router.refresh();
    } catch (e) {
      console.error("Move failed:", e);
    } finally {
      setMoving(null);
    }
  }

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {stages.map((stage) => {
        const partners = columns[stage] || [];
        return (
          <div
            key={stage}
            className="min-w-[220px] max-w-[260px] flex-shrink-0"
          >
            <div
              className={`rounded-t-md px-3 py-1.5 text-xs font-medium ${stageColor(stage)}`}
            >
              {STAGE_LABELS[stage] || stage} ({partners.length})
            </div>
            <div className="rounded-b-md border border-t-0 bg-gray-50 p-2 space-y-2 min-h-[200px]">
              {partners.map((p) => (
                <div
                  key={p.id}
                  className="rounded bg-white border p-2 text-xs shadow-sm"
                >
                  <Link
                    href={`/partners/${p.id}`}
                    className="font-medium text-blue-600 hover:underline block truncate"
                  >
                    {p.name}
                  </Link>
                  <div className="text-gray-400 truncate">{p.domain}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-gray-500">{p.country}</span>
                    <span className="ml-auto font-medium">
                      {formatScore(p.score_total)}
                    </span>
                  </div>
                  {p.blocker && (
                    <div className="text-red-500 mt-1 truncate">
                      {p.blocker.replace(/_/g, " ")}
                    </div>
                  )}
                  {/* Move buttons */}
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    {(ALLOWED_TRANSITIONS[stage] || []).map((to) => (
                      <button
                        key={to}
                        onClick={() => handleMove(p.id, to)}
                        disabled={moving === p.id}
                        className="rounded border px-1.5 py-0.5 text-[10px] hover:bg-gray-100 disabled:opacity-50"
                      >
                        {to === "lost" ? "Lost" : (STAGE_LABELS[to] || to)}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
