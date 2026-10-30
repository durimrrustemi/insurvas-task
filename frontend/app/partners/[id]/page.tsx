import {
  getPartner,
  getSignals,
  getContacts,
  getMessages,
  getActivities,
  getReadiness,
} from "@/lib/api";
import { StageBadge } from "@/components/StageBadge";
import { ScoreBreakdown } from "@/components/ScoreBreakdown";
import { MessageReview } from "@/components/MessageReview";
import { StageActions } from "@/components/StageActions";
import { formatDate } from "@/lib/utils";
import Link from "next/link";

export default async function PartnerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let partner, signals, contacts, messages, activities, readiness;
  try {
    [partner, signals, contacts, messages, activities, readiness] = await Promise.all([
      getPartner(id),
      getSignals(id),
      getContacts(id),
      getMessages(id),
      getActivities(id),
      getReadiness(id),
    ]);
  } catch {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>Could not load partner. Make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl">
      <Link href="/partners" className="text-sm text-gray-500 hover:text-gray-700 mb-4 block">
        &larr; Back to partners
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">{partner.name}</h1>
          <p className="text-sm text-gray-500">
            {partner.domain} &middot; {partner.country}
            {partner.city && `, ${partner.city}`}
          </p>
        </div>
        <StageBadge stage={partner.stage} />
      </div>

      {partner.blocker && (
        <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          Blocker: {partner.blocker.replace(/_/g, " ")}
        </div>
      )}

      {/* Stage actions + readiness checklist */}
      <StageActions partner={partner} readiness={readiness} />

      {/* Score breakdown with expandable evidence */}
      <ScoreBreakdown partner={partner} signals={signals} />

      {/* Contacts */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-3">Contacts ({contacts.length})</h2>
        {contacts.length === 0 ? (
          <p className="text-sm text-gray-500">No contacts yet.</p>
        ) : (
          <div className="space-y-2">
            {contacts.map((c) => (
              <div key={c.id} className="rounded border p-3 text-sm">
                <span className="font-medium">{c.name}</span>
                {c.role && <span className="text-gray-500"> &middot; {c.role}</span>}
                <div className="text-xs text-gray-500 mt-1">
                  {c.email && <span className="mr-3">{c.email}</span>}
                  {c.whatsapp && <span className="mr-3">WA: {c.whatsapp}</span>}
                  {c.linkedin_url && (
                    <a
                      href={c.linkedin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500"
                    >
                      LinkedIn
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Messages with review controls */}
      <MessageReview partnerId={id} messages={messages} />

      {/* Activity timeline */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-3">Activity ({activities.length})</h2>
        {activities.length === 0 ? (
          <p className="text-sm text-gray-500">No activity yet.</p>
        ) : (
          <div className="space-y-2">
            {activities.map((a) => (
              <div key={a.id} className="flex gap-3 text-sm">
                <span className="text-gray-400 w-28 shrink-0">{formatDate(a.at)}</span>
                <span className="font-medium capitalize">{a.kind.replace(/_/g, " ")}</span>
                {a.body && <span className="text-gray-600">{a.body}</span>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Partner info */}
      <section className="mb-8">
        <h2 className="text-lg font-medium mb-3">Info</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt className="text-gray-500">Website</dt>
          <dd>
            {partner.website ? (
              <a
                href={partner.website}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline"
              >
                {partner.website}
              </a>
            ) : (
              "\u2014"
            )}
          </dd>
          <dt className="text-gray-500">Type</dt>
          <dd>{partner.type}</dd>
          <dt className="text-gray-500">Timezone</dt>
          <dd>{partner.timezone || "\u2014"}</dd>
          <dt className="text-gray-500">Stage entered</dt>
          <dd>{formatDate(partner.stage_entered_at)}</dd>
          <dt className="text-gray-500">Created</dt>
          <dd>{formatDate(partner.created_at)}</dd>
        </dl>
      </section>
    </div>
  );
}
