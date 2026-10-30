"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createContact } from "@/lib/api";

const FIELDS = [
  { key: "name", label: "Name", placeholder: "Maria Santos" },
  { key: "role", label: "Role", placeholder: "Operations Manager" },
  { key: "email", label: "Email", placeholder: "" },
  { key: "whatsapp", label: "WhatsApp", placeholder: "+63..." },
  { key: "linkedin_url", label: "LinkedIn URL", placeholder: "https://linkedin.com/in/..." },
] as const;

type Field = (typeof FIELDS)[number]["key"];

const EMPTY: Record<Field, string> = {
  name: "",
  role: "",
  email: "",
  whatsapp: "",
  linkedin_url: "",
};

export function AddContact({ partnerId }: { partnerId: string }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [values, setValues] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!values.name.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      // Send only filled-in fields; the API treats missing ones as unknown.
      const data = Object.fromEntries(
        Object.entries(values)
          .map(([k, v]) => [k, v.trim()])
          .filter(([, v]) => v !== ""),
      ) as { name: string };
      await createContact(partnerId, data);
      setValues(EMPTY);
      setOpen(false);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="mt-2 text-sm text-gray-500 hover:text-gray-700"
      >
        + Add contact
      </button>
    );
  }

  return (
    <div className="mt-2 rounded border p-3">
      {error && <div className="mb-2 rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</div>}
      <div className="grid grid-cols-2 gap-2">
        {FIELDS.map((f) => (
          <label key={f.key} className="text-xs text-gray-600">
            {f.label}
            <input
              className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              placeholder={f.placeholder}
              value={values[f.key]}
              onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
            />
          </label>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <button
          onClick={save}
          disabled={saving}
          className="rounded bg-gray-800 px-3 py-1 text-sm text-white hover:bg-gray-900 disabled:opacity-50"
        >
          Save contact
        </button>
        <button
          onClick={() => setOpen(false)}
          className="rounded border px-3 py-1 text-sm hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
