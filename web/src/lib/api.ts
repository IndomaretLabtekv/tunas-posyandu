import type {
  AuthResponse,
  CaseDetail,
  CaseSummary,
  GrowthCheck,
  MotherChild,
  MotherTimeline,
  Role,
  Session,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SESSION_KEY = "tunas.session";

async function parseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail || `Permintaan gagal (${response.status})`;
  } catch {
    return `Permintaan gagal (${response.status})`;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (authenticated) {
    const session = getSession();
    if (!session) throw new Error("Silakan masuk terlebih dahulu.");
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<T>;
}

export function saveSession(auth: AuthResponse): Session {
  const session: Session = { ...auth.user, accessToken: auth.access_token };
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  return session;
}

export function getSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

export function roleHome(role: Role): string {
  if (role === "mother") return "/ibu";
  if (role === "kader") return "/kader";
  return "/ahli-gizi";
}

export function login(name: string, password: string, scopeKey: string) {
  return request<AuthResponse>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ name, password, scope_key: scopeKey }) },
    false,
  );
}

export function demoLogin(role: Role) {
  return request<AuthResponse>(
    "/api/auth/demo-login",
    { method: "POST", body: JSON.stringify({ role }) },
    false,
  );
}

export function registerMother(name: string, password: string, scopeKey: string) {
  return request<AuthResponse>(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify({ name, password, scope_key: scopeKey }) },
    false,
  );
}

export function createChild(payload: { name: string; sex: "M" | "F"; birth_date: string }) {
  return request<MotherChild>("/api/mother/children", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMotherChildren() {
  return request<MotherChild[]>("/api/mother/children");
}

export function submitGrowthCheck(childId: number, weightKg: number, image: File) {
  const body = new FormData();
  body.append("child_id", String(childId));
  body.append("weight_kg", String(weightKg));
  body.append("image", image);
  return request<GrowthCheck>("/api/mother/growth-checks", { method: "POST", body });
}

export function getMotherTimeline(childId: number) {
  return request<MotherTimeline>(`/api/mother/children/${childId}/timeline`);
}

export function listKaderCases() {
  return request<CaseSummary[]>("/api/kader/cases");
}

export function getKaderCase(caseId: number) {
  return request<CaseDetail>(`/api/kader/cases/${caseId}`);
}

export function assignCase(caseId: number, notes = "") {
  return request<CaseDetail>(`/api/kader/cases/${caseId}/assign`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export function recordHomeVisit(
  caseId: number,
  payload: { notes: string; weight_kg: number | null; length_cm: number | null },
) {
  return request<CaseDetail>(`/api/kader/cases/${caseId}/home-visit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyCase(
  caseId: number,
  payload: { weight_kg: number; length_cm: number; outcome: "verified_risk" | "resolved"; notes: string },
) {
  return request<CaseDetail>(`/api/kader/cases/${caseId}/verify`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listNutritionistCases() {
  return request<CaseSummary[]>("/api/nutritionist/cases");
}

export function getNutritionistCase(caseId: number) {
  return request<CaseDetail>(`/api/nutritionist/cases/${caseId}`);
}

export function recordDecision(
  caseId: number,
  payload: { action: string; notes: string; resolve: boolean },
) {
  return request<CaseDetail>(`/api/nutritionist/cases/${caseId}/decision`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function referCase(caseId: number, destination: string, notes: string) {
  return request<CaseDetail>(`/api/nutritionist/cases/${caseId}/referral`, {
    method: "POST",
    body: JSON.stringify({ destination, notes }),
  });
}
