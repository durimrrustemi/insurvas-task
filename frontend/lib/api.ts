const isServer = typeof window === "undefined";
const API_BASE = isServer
  ? (process.env.API_URL || "http://api:8000")
  : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(error.error?.message || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Partner {
  id: string;
  name: string;
  domain: string;
  website: string | null;
  country: string;
  city: string | null;
  timezone: string | null;
  type: "bpo" | "vendor";
  stage: string;
  stage_entered_at: string | null;
  owner_note: string | null;
  blocker: string | null;
  score_total: number | null;
  score_english: number | null;
  score_insurance: number | null;
  score_size: number | null;
  score_compliance: number | null;
  engagement_terms: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PartnerList {
  items: Partner[];
  total: number;
  limit: number;
  offset: number;
}

export interface Signal {
  id: string;
  partner_id: string;
  criterion: string;
  key: string;
  value: number;
  weight: number;
  source_url: string | null;
  matched_text: string | null;
  created_at: string;
}

export interface Contact {
  id: string;
  partner_id: string;
  name: string;
  role: string | null;
  email: string | null;
  linkedin_url: string | null;
  whatsapp: string | null;
  source_url: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  partner_id: string;
  channel: string;
  sequence: number;
  subject: string | null;
  body: string;
  angle: string | null;
  evidence_ids: string[] | null;
  status: string;
  send_after: string | null;
  created_at: string;
}

export interface Activity {
  id: string;
  partner_id: string;
  kind: string;
  channel: string | null;
  body: string | null;
  at: string;
}

export async function getPartners(params?: {
  country?: string;
  stage?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<PartnerList> {
  const searchParams = new URLSearchParams();
  if (params?.country) searchParams.set("country", params.country);
  if (params?.stage) searchParams.set("stage", params.stage);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const query = searchParams.toString();
  return apiFetch<PartnerList>(`/partners${query ? `?${query}` : ""}`);
}

export async function getPartner(id: string): Promise<Partner> {
  return apiFetch<Partner>(`/partners/${id}`);
}

export async function getSignals(partnerId: string): Promise<Signal[]> {
  return apiFetch<Signal[]>(`/partners/${partnerId}/signals`);
}

export async function getContacts(partnerId: string): Promise<Contact[]> {
  return apiFetch<Contact[]>(`/partners/${partnerId}/contacts`);
}

export async function getMessages(partnerId: string): Promise<Message[]> {
  return apiFetch<Message[]>(`/partners/${partnerId}/messages`);
}

export async function getActivities(partnerId: string): Promise<Activity[]> {
  return apiFetch<Activity[]>(`/partners/${partnerId}/activities`);
}

export async function transitionStage(partnerId: string, to: string, reason?: string) {
  return apiFetch(`/partners/${partnerId}/stage`, {
    method: "POST",
    body: JSON.stringify({ to, reason }),
  });
}

export async function updateMessage(messageId: string, data: { status?: string; body?: string; subject?: string }) {
  return apiFetch(`/messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function generateOutreach(partnerId: string, channels?: string[]): Promise<Message[]> {
  return apiFetch<Message[]>(`/partners/${partnerId}/outreach`, {
    method: "POST",
    body: JSON.stringify(channels ? { channels } : {}),
  });
}

export async function scorePartner(partnerId: string): Promise<Partner> {
  return apiFetch<Partner>(`/partners/${partnerId}/score`, { method: "POST" });
}

export interface BoardData {
  columns: Record<string, Partner[]>;
}

export interface AttentionItem {
  partner: Partner;
  reasons: string[];
  priority: number;
  days_since_touch: number;
  days_in_stage: number;
}

export interface AttentionData {
  items: AttentionItem[];
}

export async function getBoard(): Promise<BoardData> {
  return apiFetch<BoardData>("/board");
}

export async function getAttention(): Promise<AttentionData> {
  return apiFetch<AttentionData>("/attention");
}

export async function getConfig(): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>("/config");
}

export async function startDiscoveryRun(country: string, limit: number = 30) {
  return apiFetch("/discovery/runs", {
    method: "POST",
    body: JSON.stringify({ country, limit }),
  });
}

export async function getDiscoveryRuns() {
  return apiFetch<Array<Record<string, unknown>>>("/discovery/runs");
}

export async function createActivity(partnerId: string, data: { kind: string; channel?: string; body?: string }) {
  return apiFetch(`/partners/${partnerId}/activities`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
