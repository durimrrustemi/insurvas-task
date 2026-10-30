"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Partner, Signal, Contact } from "@/lib/types";
import { transitionStage, createActivity } from "@/lib/api";

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  found: ["contacted", "lost"],
  contacted: ["replied", "lost"],
  replied: ["in_talks", "lost"],
  in_talks: ["test_calls", "lost"],
  test_calls: ["signed", "lost"],
  signed: ["lost"],
  lost: ["found"],
};

const STAGE_LABELS: Record<string, string> = {
  found: "Found",
  contacted: "Contacted",
  replied: "Replied",
  in_talks: "In Talks",
  test_calls: "Test Calls",
  signed: "Signed",
  lost: "Lost",
};

const READINESS: Record<string, Array<{ label: string; check: (p: Partner, signals: Signal[], contacts: Contact[]) => boolean }>> = {
  test_calls: [
    { label: "Has a named contact", check: (_p, _s, contacts) => contacts.length > 0 },
    { label: "Compliance signal present", check: (_p, signals) => signals.some((s) => s.criterion === "compliance") },
    { label: "Score computed", check: (p) => p.score_total !== null },
  ],
  signed: [
    { label: "Has a named contact", check: (_p, _s, contacts) => contacts.length > 0 },
    { label: "Score computed", check: (p) => p.score_total !== null },
  ],
};

export function StageActions({
  partner,
  signals,
  contacts,
}: {
  partner: Partner;
  signals: Signal[];
  contacts: Contact[];
}) {
  const router = useRouter();
  const [moving, setMoving] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [showNote, setShowNote] = useState(false);

  const allowed = ALLOWED_TRANSITIONS[partner.stage] || [];

  async function handleTransition(to: string) {
    setMoving(true);
    try {
      await transitionStage(partner.id, to);
      router.refresh();
    } catch (e) {
      console.error("Transition failed:", e);
    } finally {
      setMoving(false);
    }
  }

  async function handleAddNote() {
    if (!noteText.trim()) return;
    try {
      await createActivity(partner.id, { kind: "note", body: noteText });
      setNoteText("");
      setShowNote(false);
      router.refresh();
    } catch (e) {
      console.error("Add note failed:", e);
    }
  }

  // Show readiness checklist for next stage
  const nextStage = allowed.find((s) => s !== "lost");
  const readiness = nextStage ? READINESS[nextStage] : undefined;

  return (
    <section className="mb-8">
      <h2 className="text-lg font-medium mb-3">Actions</h2>

      {/* Readiness checklist */}
      {readiness && (
        <div className="mb-3 rounded border p-3">
          <p className="text-xs font-medium text-gray-600 mb-2">
            Readiness for {STAGE_LABELS[nextStage!] || nextStage}:
          </p>
          {readiness.map((r, i) => {
            const ok = r.check(partner, signals, contacts);
            return (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className={ok ? "text-green-500" : "text-red-400"}>
                  {ok ? "\u2713" : "\u2717"}
                </span>
                <span className={ok ? "text-gray-700" : "text-gray-400"}>{r.label}</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Transition buttons */}
      <div className="flex gap-2 flex-wrap">
        {allowed.map((to) => (
          <button
            key={to}
            onClick={() => handleTransition(to)}
            disabled={moving}
            className={`rounded px-3 py-1 text-sm disabled:opacity-50 ${
              to === "lost"
                ? "border border-red-300 text-red-600 hover:bg-red-50"
                : "bg-blue-500 text-white hover:bg-blue-600"
            }`}
          >
            {moving ? "..." : `Move to ${STAGE_LABELS[to] || to}`}
          </button>
        ))}
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
