export type Role = "mother" | "kader" | "nutritionist";

export type AuthUser = {
  id: number;
  name: string;
  role: Role;
  scope_key: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type Session = AuthUser & { accessToken: string };

export type MotherChild = {
  child_id: number;
  name: string;
  sex: "M" | "F";
  birth_date: string;
  scope_key: string;
  next_due_at: string | null;
};

export type GrowthCheck = {
  growth_check_id: number;
  child_id: number;
  source: string;
  age_days: number;
  weight_kg: number;
  length_cm: number | null;
  haz: number | null;
  mode: string;
  confidence: number;
  low_confidence: boolean;
  qc_reasons: string[];
  screening_status: "normal" | "needs_review";
  verification_status: "unverified" | "verified";
  reason_codes?: string[];
  case_id: number | null;
  case_status: string | null;
  measured_at: string;
  next_due_at: string;
};

export type MotherTimeline = {
  child: MotherChild;
  checks: GrowthCheck[];
};

export type CaseSummary = {
  case_id: number;
  child_id: number;
  child_name: string;
  status: string;
  priority: string;
  reason_codes: string[];
  source: string;
  screening_status: string;
  age_days: number;
  weight_kg: number;
  length_cm: number | null;
  haz: number | null;
  mode: string;
  confidence: number;
  submitted_at: string;
  next_due_at: string;
  days_since_submission: number;
  overdue: boolean;
};

export type CaseAction = {
  action_id: number;
  actor_id: number;
  action_type: string;
  notes: string;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type CaseDetail = {
  case: CaseSummary;
  checks: GrowthCheck[];
  actions: CaseAction[];
};
