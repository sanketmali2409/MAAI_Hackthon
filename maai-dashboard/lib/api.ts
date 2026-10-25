// Server-side data helpers for the dashboard. These run in React Server
// Components and hit our own /api proxy (which injects the backend key).

const SELF = process.env.DASHBOARD_SELF_URL || "http://localhost:3000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${SELF}/api/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

export type Session = {
  id: string;
  mother_id: string | null;
  subject_name: string | null;
  subject_phone: string | null;
  language: string;
  status: string;
  total_score: number | null;
  risk_band: string | null;
  self_harm_flag: boolean;
  transcript?: string | null;
  created_at: string;
  completed_at: string | null;
};

export type Escalation = {
  id: string;
  session_id: string | null;
  mother_id: string | null;
  reason: string;
  risk_band: string | null;
  total_score: number | null;
  status: string;
  notified: boolean;
  notes: string | null;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
};

export type Mother = {
  id: string;
  name: string | null;
  phone: string;
  language: string;
  call_cadence: string;
  next_call_at: string | null;
  active: boolean;
  notes: string | null;
  created_at: string;
};

export const listSessions = () => get<Session[]>("v1/epds/sessions");
export const listEscalations = (status?: string) =>
  get<Escalation[]>(`v1/epds/escalations${status ? `?status=${status}` : ""}`);
export const listMothers = () => get<Mother[]>("v1/mothers");
export const getSession = (id: string) =>
  get<{ session: Session; result: any; answers: Record<string, number> }>(
    `v1/epds/sessions/${id}`
  );
export type Consent = {
  id: string;
  consented: boolean;
  scope: string | null;
  method: string | null;
  recorded_at: string;
  revoked_at: string | null;
};

export const getMother = (id: string) =>
  get<{ mother: Mother; consent: Consent | null; has_active_consent: boolean; sessions: Session[] }>(
    `v1/mothers/${id}`
  );
export const getConsentHistory = (id: string) =>
  get<Consent[]>(`v1/mothers/${id}/consent`);
