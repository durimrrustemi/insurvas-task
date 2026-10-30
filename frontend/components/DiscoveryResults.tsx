import Link from "next/link";
import type { DiscoveryCandidate } from "@/lib/types";
import { formatScore } from "@/lib/utils";

export function DiscoveryResults({ candidates }: { candidates: DiscoveryCandidate[] }) {
  if (candidates.length === 0) {
    return <p className="text-sm text-gray-500">This run found no partners.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2 pr-4">Partner</th>
            <th className="pb-2 pr-4">Type</th>
            <th className="pb-2 pr-4">Score</th>
            <th className="pb-2 pr-4">Insurance</th>
            <th className="pb-2 pr-4">English</th>
            <th className="pb-2 pr-4"></th>
          </tr>
        </thead>
        <tbody>
          {candidates.map(({ partner, new: isNew }) => (
            <tr key={partner.id} className="border-b hover:bg-gray-50">
              <td className="py-2 pr-4">
                <Link
                  href={`/partners/${partner.id}`}
                  className="text-blue-600 hover:underline font-medium"
                >
                  {partner.name}
                </Link>
                <div className="text-xs text-gray-400">{partner.domain}</div>
              </td>
              <td className="py-2 pr-4">{partner.type === "vendor" ? "Lead vendor" : "BPO"}</td>
              <td className="py-2 pr-4 font-medium">{formatScore(partner.score_total)}</td>
              <td className="py-2 pr-4">{formatScore(partner.score_insurance)}</td>
              <td className="py-2 pr-4">{formatScore(partner.score_english)}</td>
              <td className="py-2 pr-4">
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${
                    isNew ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {isNew ? "new" : "already known"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
