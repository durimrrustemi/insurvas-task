"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Message } from "@/lib/types";
import { updateMessage, generateOutreach } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  approved: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  sent: "bg-blue-100 text-blue-700",
};

export function MessageReview({ partnerId, messages }: { partnerId: string; messages: Message[] }) {
  const router = useRouter();
  const [generating, setGenerating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    setError(null);
    try {
      await generateOutreach(partnerId);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setGenerating(false);
    }
  }

  async function handleStatusChange(messageId: string, status: string) {
    setError(null);
    try {
      await updateMessage(messageId, { status });
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  function startEdit(msg: Message) {
    setEditingId(msg.id);
    setEditBody(msg.body);
    setEditSubject(msg.subject || "");
  }

  async function saveEdit(messageId: string) {
    try {
      await updateMessage(messageId, {
        body: editBody,
        subject: editSubject || undefined,
      });
      setEditingId(null);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  // Group messages by channel
  const grouped: Record<string, Message[]> = {};
  for (const m of messages) {
    (grouped[m.channel] ??= []).push(m);
  }

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium">Messages ({messages.length})</h2>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="rounded bg-blue-500 px-3 py-1 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Generate outreach"}
        </button>
      </div>

      {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {messages.length === 0 ? (
        <p className="text-sm text-gray-500">
          No messages yet. Click &quot;Generate outreach&quot; to create drafts.
        </p>
      ) : (
        Object.entries(grouped).map(([channel, msgs]) => (
          <div key={channel} className="mb-4">
            <h3 className="text-sm font-medium text-gray-600 uppercase mb-2">{channel}</h3>
            <div className="space-y-2">
              {msgs
                .sort((a, b) => a.sequence - b.sequence)
                .map((m) => (
                  <div key={m.id} className="rounded border p-3 text-sm">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium capitalize">
                        #{m.sequence} — {m.angle ? "angle" : m.channel}
                      </span>
                      <span
                        className={`ml-auto rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[m.status] || STATUS_STYLES.draft}`}
                      >
                        {m.status}
                      </span>
                    </div>

                    {m.angle && (
                      <p className="text-xs text-gray-500 italic mb-1">Angle: {m.angle}</p>
                    )}

                    {editingId === m.id ? (
                      <div className="space-y-2">
                        {m.subject !== null && (
                          <input
                            className="w-full rounded border px-2 py-1 text-xs"
                            value={editSubject}
                            onChange={(e) => setEditSubject(e.target.value)}
                            placeholder="Subject"
                          />
                        )}
                        <textarea
                          className="w-full rounded border px-2 py-1 text-xs min-h-[80px]"
                          value={editBody}
                          onChange={(e) => setEditBody(e.target.value)}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => saveEdit(m.id)}
                            className="rounded bg-blue-500 px-2 py-0.5 text-xs text-white hover:bg-blue-600"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingId(null)}
                            className="rounded border px-2 py-0.5 text-xs hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        {m.subject && (
                          <p className="font-medium text-xs mb-1">Subject: {m.subject}</p>
                        )}
                        <p className="text-gray-700 whitespace-pre-wrap">{m.body}</p>

                        <div className="flex gap-2 mt-2">
                          {m.status === "draft" && (
                            <>
                              <button
                                onClick={() => handleStatusChange(m.id, "approved")}
                                className="rounded bg-green-500 px-2 py-0.5 text-xs text-white hover:bg-green-600"
                              >
                                Approve
                              </button>
                              <button
                                onClick={() => handleStatusChange(m.id, "rejected")}
                                className="rounded bg-red-500 px-2 py-0.5 text-xs text-white hover:bg-red-600"
                              >
                                Reject
                              </button>
                            </>
                          )}
                          {m.status === "approved" && (
                            <button
                              onClick={() => handleStatusChange(m.id, "sent")}
                              className="rounded bg-blue-500 px-2 py-0.5 text-xs text-white hover:bg-blue-600"
                            >
                              Mark sent
                            </button>
                          )}
                          <button
                            onClick={() => startEdit(m)}
                            className="rounded border px-2 py-0.5 text-xs hover:bg-gray-50"
                          >
                            Edit
                          </button>
                          {m.status !== "draft" && m.status !== "sent" && (
                            <button
                              onClick={() => handleStatusChange(m.id, "draft")}
                              className="rounded border px-2 py-0.5 text-xs hover:bg-gray-50"
                            >
                              Reset to draft
                            </button>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                ))}
            </div>
          </div>
        ))
      )}
    </section>
  );
}
