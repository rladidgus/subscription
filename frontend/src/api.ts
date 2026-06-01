const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export interface ScoreRequest {
  age: number;
  is_homeless: boolean;
  homeless_years: number;
  dependents_count: number;
  subscription_account_years: number;
  subscription_account_months: number;
  marital_status: string;
}

export interface ScoreResponse {
  total_score: number;
  homeless_score: number;
  dependents_score: number;
  account_score: number;
  warnings: string[];
}

export interface ApplyHomeClassifyRequest {
  user_score: number;
  apartment_name?: string;
  is_eligible: boolean;
  eligibility_reasons: string[];
  limit: number;
}

export interface ApplyHomeClassifiedResult {
  apartment_name: string;
  house_manage_no: string;
  pblanc_no: string;
  model_no: string;
  house_type: string;
  region_code: string;
  announcement_date?: string | null;
  reside_secd: string;
  subscription_rank_code: string;
  predicted_cutoff_score: number | null;
  actual_cutoff_score?: number | null;
  model_name: string;
  prediction_status: string;
  shortage_probability?: number | null;
  competition_probability?: number | null;
  region_mae?: number | null;
  region_confidence_level?: string | null;
  region_confidence_label?: string | null;
  confidence_note: string;
  user_score: number;
  score_gap: number | null;
  category: string;
  category_label: string;
  support_level: string;
  support_label: string;
  support_note: string;
  eligibility_status: string;
  eligibility_reasons: string[];
}

export interface ApplyHomeClassificationResponse {
  available_now: ApplyHomeClassifiedResult[];
  prepare_later: ApplyHomeClassifiedResult[];
  difficult: ApplyHomeClassifiedResult[];
  not_eligible: ApplyHomeClassifiedResult[];
}

export interface ApplyHomeCutoffResponse {
  results: Omit<ApplyHomeClassifiedResult, "user_score" | "score_gap" | "category" | "category_label" | "support_level" | "support_label" | "support_note" | "eligibility_status" | "eligibility_reasons">[];
}

export type ApplyHomeListing = ApplyHomeCutoffResponse["results"][number];

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `요청 실패: ${res.status}`);
  }
  return res.json();
}

function postJson<T>(url: string, body: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  health: () => fetchJson<{ status: string }>("/health"),
  calculateScore: (body: ScoreRequest) => postJson<ScoreResponse>("/score/calculate", body),
  classifyApplyHome: (body: ApplyHomeClassifyRequest) =>
    postJson<ApplyHomeClassificationResponse>("/predict/applyhome-classify", body),
  predictApplyHome: (body: { apartment_name?: string; region_code?: string; limit?: number }) =>
    postJson<ApplyHomeCutoffResponse>("/predict/applyhome-cutoff", body),
};
