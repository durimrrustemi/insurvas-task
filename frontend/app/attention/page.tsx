import { getAttention } from "@/lib/api";
import { StageBadge } from "@/components/StageBadge";
import { formatScore } from "@/lib/utils";
import Link from "next/link";

export default async function AttentionPage() {
  let data;
  try {
    data = await getAttention();
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not load attention data. Make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Needs Attention</h1>
        <span className="text-sm text-gray-500">{data.items.length} partners</span>
      </div>

      {data.items.length === 0 ? (
        <p className="text-center py-12 text-gray-500">All clear — no partners need attention right now.</p>
      ) : (
        <div className="space-y-3">
          {data.items.map((item) => (
            <div key={item.partner.id} className="rounded border p-4 hover:bg-gray-50">
              <div className="flex items-start justify-between">
                <div>
                  <Link
                    href={`/partners/${item.partner.id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {item.partner.name}
                  </Link>
                  <span className="text-sm text-gray-400 ml-2">{item.partner.domain}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{formatScore(item.partner.score_total)}</span>
                  <StageBadge stage={item.partner.stage} />
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {item.reasons.map((reason, i) => (
                  <span
                    key={i}
                    className="rounded-full bg-amber-50 px-2.5 py-0.5 text-xs text-amber-700 border border-amber-200"
                  >
                    {reason}
                  </span>
                ))}
              </div>
              <div className="mt-1.5 text-xs text-gray-400">
                {item.partner.country}
                {item.partner.city && ` · ${item.partner.city}`}
                {` · ${item.days_since_touch}d since touch`}
                {` · ${item.days_in_stage}d in stage`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
