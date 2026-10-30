"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Partner, PartnerReadiness } from "@/lib/types";
import { transitionStage, createActivity, setGate, updatePartner } from "@/lib/api";

const STAGE_LABELS: Record<string, string> = {
  found: "Found",
  contacted: "Contacted",
  replied: "Replied",
  in_talks: "In Talks",
  test_calls: "Test Calls",
  signed: "Signed",
  lost: "Lost",
};

const BLOCKERS = [
  "no_response",
  "pricing",
  "compliance",
  "capacity",
  "waiting_on_them",
  "waiting_on_us",
];

// Field labels only; which terms are required per stage comes from the API readiness checks.
const TERM_FIELDS: Array<{ key: string; label: string }> = [
  { key: "test_batch_size", label: "Test batch size" },
  { key: "price_per_transfer", label: "Price per transfer (USD)" },
  { key: "daily_volume", label: "Daily volume" },
  { key: "hours", label: "Hours" },
  { key: "quality_threshold", label: "Quality threshold" },
];

const TERMS_STAGES = ["in_talks", "test_calls", "signed"];

export function StageActions({
  partner,
  readiness,
}: {
  partner: Partner;
  readiness: PartnerReadiness;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noteText, setNoteText] = useState("");
  const [showNote, setShowNote] = useState(false);
  const [lostReason, setLostReason] = useState("");
  const [terms, setTerms] = useState<Record<string, string>>(
    Object.fromEntries(
      TERM_FIELDS.map((f) => [f.key, String(partner.engagement_terms?.[f.key] ?? "")]),
    ),
  );

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  function saveTerms() {
    const cleaned = Object.fromEntries(Object.entries(terms).filter(([, v]) => v.trim() !== ""));
    return run(() =>
      updatePartner(partner.id, {
        engagement_terms: { ...(partner.engagement_terms ?? {}), ...cleaned },
      }),
    );
  }

  async function handleAddNote() {
    if (!noteText.trim()) return;
    await run(() => createActivity(partner.id, { kind: "note", body: noteText }));
    setNoteText("");
    setShowNote(false);
  }

  const forward = readiness.transitions.filter((t) => t.to !== "lost");
  const canLose = readiness.transitions.some((t) => t.to === "lost");

  return (
    <section className="mb-8">
      <h2 className="text-lg font-medium mb-3">Actions</h2>

      {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {/* Readiness checklist, computed by the API */}
      {forward.map((t) =>
        t.checks.length === 0 ? null : (
          <div key={t.to} className="mb-3 rounded border p-3">
            <p className="text-xs font-medium text-gray-600 mb-2">
              Readiness for {STAGE_LABELS[t.to] || t.to}:
            </p>
            {t.checks.map((c) => (
              <div key={c.key} className="flex items-center gap-2 text-xs">
                <span className={c.ok ? "text-green-500" : "text-red-400"}>{c.ok ? "✓" : "✗"}</span>
                <span className={c.ok ? "text-gray-700" : "text-gray-400"}>{c.label}</span>
              </div>
            ))}
          </div>
        ),
      )}

      {/* Transition buttons */}
      <div className="flex gap-2 flex-wrap items-center">
        {forward.map((t) => (
          <button
            key={t.to}
            onClick={() => run(() => transitionStage(partner.id, t.to))}
            disabled={busy || !t.ready}
            title={t.ready ? undefined : "Readiness checks not met"}
            className="rounded px-3 py-1 text-sm bg-blue-500 text-white hover:bg-blue-600 disabled:opacity-50"
          >
            {`Move to ${STAGE_LABELS[t.to] || t.to}`}
          </button>
        ))}
        {canLose && (
          <span className="flex gap-1 items-center">
            <input
              className="rounded border px-2 py-1 text-sm w-48"
              placeholder="Lost reason (optional)"
              value={lostReason}
              onChange={(e) => setLostReason(e.target.value)}
            />
            <button
              onClick={() =>
                run(() => transitionStage(partner.id, "lost", lostReason.trim() || undefined))
              }
              disabled={busy}
              className="rounded px-3 py-1 text-sm border border-red-300 text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              Mark lost
            </button>
          </span>
        )}
      </div>

      {/* Gates */}
      <div className="mt-4 rounded border p-3">
        <p className="text-xs font-medium text-gray-600 mb-2">Gates (hard requirements)</p>
        {Object.entries(readiness.gates).map(([gate, status]) => (
          <div key={gate} className="flex items-center gap-2 text-xs mb-1">
            <span className="w-24 font-medium">{gate.replace(/_/g, " ")}</span>
            <span
              className={
                status === "confirmed"
                  ? "text-green-600"
                  : status === "no"
                    ? "text-red-600"
                    : "text-amber-600"
              }
            >
              {status}
            </span>
            {status !== "confirmed" && (
              <button
                onClick={() => run(() => setGate(partner.id, gate, true))}
                disabled={busy}
                className="rounded border px-2 py-0.5 hover:bg-gray-50 disabled:opacity-50"
              >
                Confirm
              </button>
            )}
            {status !== "no" && partner.stage !== "lost" && (
              <button
                onClick={() => run(() => setGate(partner.id, gate, false))}
                disabled={busy}
                title="Fails the gate and marks the partner lost"
                className="rounded border border-red-200 px-2 py-0.5 text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                No
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Engagement terms */}
      {TERMS_STAGES.includes(partner.stage) && (
        <div className="mt-4 rounded border p-3">
          <p className="text-xs font-medium text-gray-600 mb-2">Engagement terms</p>
          <div className="grid grid-cols-2 gap-2">
            {TERM_FIELDS.map((f) => (
              <label key={f.key} className="text-xs text-gray-600">
                {f.label}
                <input
                  className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
                  value={terms[f.key]}
                  onChange={(e) => setTerms({ ...terms, [f.key]: e.target.value })}
                />
              </label>
            ))}
          </div>
          <button
            onClick={saveTerms}
            disabled={busy}
            className="mt-2 rounded bg-gray-800 px-3 py-1 text-sm text-white hover:bg-gray-900 disabled:opacity-50"
          >
            Save terms
          </button>
        </div>
      )}

      {/* Blocker */}
      <div className="mt-4 flex items-center gap-2 text-sm">
        <span className="text-gray-600">Blocker:</span>
        <select
          className="rounded border px-2 py-1 text-sm"
          value={partner.blocker ?? ""}
          disabled={busy}
          onChange={(e) =>
            run(() => updatePartner(partner.id, { blocker: e.target.value || null }))
          }
        >
          <option value="">none</option>
          {BLOCKERS.map((b) => (
            <option key={b} value={b}>
              {b.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {/* Add note */}
      <div className="mt-3">
        {showNote ? (
          <div className="space-y-2">
            <textarea
              className="w-full rounded border px-2 py-1 text-sm min-h-[60px]"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Add a note..."
            />
            <div className="flex gap-2">
              <button
                onClick={handleAddNote}
                className="rounded bg-gray-800 px-3 py-1 text-sm text-white hover:bg-gray-900"
              >
                Save note
              </button>
              <button
                onClick={() => setShowNote(false)}
                className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setShowNote(true)}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            + Add note
          </button>
        )}
      </div>
    </section>
  );
}
