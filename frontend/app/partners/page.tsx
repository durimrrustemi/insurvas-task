import { getPartners } from "@/lib/api";
import { StageBadge } from "@/components/StageBadge";
import { formatScore } from "@/lib/utils";
import Link from "next/link";

export default async function PartnersPage({
  searchParams,
}: {
  searchParams: Promise<{ country?: string; stage?: string; sort?: string }>;
}) {
  const params = await searchParams;
  let data;
  try {
    data = await getPartners({
      country: params.country,
      stage: params.stage,
      sort: params.sort || "score_total",
      limit: 50,
    });
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not connect to API. Make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Partners</h1>
        <span className="text-sm text-gray-500">{data.total} total</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Country</th>
              <th className="pb-2 pr-4">Stage</th>
              <th className="pb-2 pr-4">Score</th>
              <th className="pb-2 pr-4">English</th>
              <th className="pb-2 pr-4">Insurance</th>
              <th className="pb-2 pr-4">Size</th>
              <th className="pb-2 pr-4">Compliance</th>
              <th className="pb-2 pr-4">Blocker</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((partner) => (
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
                <td className="py-2 pr-4">{partner.country}</td>
                <td className="py-2 pr-4">
                  <StageBadge stage={partner.stage} />
                </td>
                <td className="py-2 pr-4 font-medium">{formatScore(partner.score_total)}</td>
                <td className="py-2 pr-4">{formatScore(partner.score_english)}</td>
                <td className="py-2 pr-4">{formatScore(partner.score_insurance)}</td>
                <td className="py-2 pr-4">{formatScore(partner.score_size)}</td>
                <td className="py-2 pr-4">{formatScore(partner.score_compliance)}</td>
                <td className="py-2 pr-4">
                  {partner.blocker && (
                    <span className="text-xs text-red-600">
                      {partner.blocker.replace(/_/g, " ")}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.items.length === 0 && (
        <p className="text-center py-12 text-gray-500">No partners found. Run seed or discovery first.</p>
      )}
    </div>
  );
}
