import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number | null): string {
  if (score === null) return "\u2014";
  return `${Math.round(score * 100)}%`;
}

// "in_talks" -> "In Talks". Generic, so a new stage needs no frontend change.
export function stageLabel(stage: string): string {
  return stage.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function stageColor(stage: string): string {
  const colors: Record<string, string> = {
    found: "bg-gray-100 text-gray-700",
    contacted: "bg-blue-100 text-blue-700",
    replied: "bg-green-100 text-green-700",
    in_talks: "bg-yellow-100 text-yellow-700",
    test_calls: "bg-purple-100 text-purple-700",
    signed: "bg-emerald-100 text-emerald-700",
    lost: "bg-red-100 text-red-700",
  };
  return colors[stage] || "bg-gray-100 text-gray-700";
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "\u2014";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
