import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Loader2, ShieldAlert } from "lucide-react";
import { api, type ApplyHomeClassifiedResult, type ScoreRequest, type ScoreResponse } from "../api";
import { rankLabel, residenceLabel } from "../applyHomeLabels";
import { getRegionLabel } from "../regions";

const defaultScoreForm: ScoreRequest = {
  age: 35,
  is_homeless: true,
  homeless_years: 5,
  dependents_count: 1,
  subscription_account_years: 6,
  subscription_account_months: 0,
  marital_status: "single",
};

const ageOptions = Array.from({ length: 62 }, (_, index) => 19 + index);
const homelessYearOptions = Array.from({ length: 16 }, (_, index) => index);
const dependentOptions = Array.from({ length: 7 }, (_, index) => index);
const accountYearOptions = Array.from({ length: 16 }, (_, index) => index);
const accountMonthOptions = Array.from({ length: 12 }, (_, index) => index);

function yearLabel(year: number, maxYear: number) {
  return year >= maxYear ? `${year}년 이상` : `${year}년`;
}

function dependentLabel(count: number) {
  return count >= 6 ? "6명 이상" : `${count}명`;
}

function supportTone(level: string) {
  switch (level) {
    case "optimal":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    case "safe":
      return "border-blue-200 bg-blue-50 text-blue-800";
    case "uncertain":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "stretch":
      return "border-orange-200 bg-orange-50 text-orange-800";
    case "not_eligible":
      return "border-slate-200 bg-slate-50 text-slate-700";
    default:
      return "border-rose-200 bg-rose-50 text-rose-800";
  }
}

function supportMessage(result: ApplyHomeClassifiedResult) {
  switch (result.support_level) {
    case "optimal":
      return "현재 점수로 지원 여유가 큰 편입니다.";
    case "safe":
      return "현재 점수로 비교적 안정적인 지원권입니다.";
    case "uncertain":
      return "지원은 가능하지만 결과 변동 가능성을 함께 봐야 합니다.";
    case "stretch":
      return "현재 점수로는 상향 지원에 가깝습니다.";
    case "not_eligible":
      return "입력한 자격 조건 기준으로는 먼저 자격 확인이 필요합니다.";
    default:
      return "현재 점수로는 보수적으로 검토하는 편이 좋습니다.";
  }
}

function cutoffLabel(score: number | null) {
  if (score == null) {
    return "-";
  }
  return score <= 0 ? "미달 가능" : `${score}점`;
}

function ResultCard({ result }: { result: ApplyHomeClassifiedResult }) {
  return (
    <div className={`rounded-lg border p-4 ${supportTone(result.support_level)}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs opacity-75">{result.announcement_date ?? "공고일 미상"} · {result.house_type}</p>
          <h4 className="mt-1 text-lg font-bold">{result.apartment_name}</h4>
          <p className="mt-1 text-sm opacity-80">
            {rankLabel(result.subscription_rank_code)} · {residenceLabel(result.reside_secd)}
          </p>
        </div>
        <span className="rounded-full bg-white/80 px-3 py-1 text-sm font-semibold shadow-sm">{result.support_label}</span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs opacity-70">예측 커트라인</p>
          <p className="text-2xl font-bold">{cutoffLabel(result.predicted_cutoff_score)}</p>
        </div>
        <div>
          <p className="text-xs opacity-70">내 점수 차이</p>
          <p className="text-2xl font-bold">{result.score_gap == null ? "-" : `${result.score_gap > 0 ? "+" : ""}${result.score_gap}`}</p>
        </div>
      </div>

      <p className="mt-4 rounded-lg bg-white/70 p-3 text-sm leading-6">{supportMessage(result)}</p>
      {result.eligibility_reasons.length > 0 && (
        <p className="mt-3 text-sm">제외 사유: {result.eligibility_reasons.join(", ")}</p>
      )}
      {result.shortage_probability != null && (
        <p className="mt-3 text-xs opacity-75">
          미달 가능성 {(result.shortage_probability * 100).toFixed(1)}% · 경쟁 발생 가능성{" "}
          {((result.competition_probability ?? 0) * 100).toFixed(1)}%
        </p>
      )}
    </div>
  );
}

export default function Predict() {
  const [searchParams] = useSearchParams();
  const selectedApartmentName = searchParams.get("apartment_name") ?? "";
  const selectedListing = {
    apartment_name: selectedApartmentName,
    house_manage_no: searchParams.get("house_manage_no") ?? "",
    pblanc_no: searchParams.get("pblanc_no") ?? "",
    model_no: searchParams.get("model_no") ?? "",
    house_type: searchParams.get("house_type") ?? "",
    region_code: searchParams.get("region_code") ?? "",
    region_name: searchParams.get("region_name") ?? getRegionLabel(searchParams.get("region_code") ?? ""),
    announcement_date: searchParams.get("announcement_date") ?? "",
    reside_secd: searchParams.get("reside_secd") ?? "",
    subscription_rank_code: searchParams.get("subscription_rank_code") ?? "",
  };
  const [scoreForm, setScoreForm] = useState<ScoreRequest>(defaultScoreForm);
  const [isEligible, setIsEligible] = useState(true);
  const [eligibilityReason, setEligibilityReason] = useState("");
  const [score, setScore] = useState<ScoreResponse | null>(null);
  const [results, setResults] = useState<ApplyHomeClassifiedResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateScore = <K extends keyof ScoreRequest>(key: K, value: ScoreRequest[K]) => {
    setScoreForm((current) => ({ ...current, [key]: value }));
  };

  const run = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const scoreResult = await api.calculateScore(scoreForm);
      setScore(scoreResult);
      const classifyResult = await api.classifyApplyHome({
        user_score: scoreResult.total_score,
        apartment_name: selectedApartmentName,
        is_eligible: isEligible,
        eligibility_reasons: eligibilityReason ? [eligibilityReason] : [],
        limit: 50,
      });
      const mergedResults = [
        ...classifyResult.available_now,
        ...classifyResult.prepare_later,
        ...classifyResult.difficult,
        ...classifyResult.not_eligible,
      ];
      const filteredResults = selectedListing.house_manage_no
        ? mergedResults.filter(
            (result) =>
              result.house_manage_no === selectedListing.house_manage_no &&
              result.pblanc_no === selectedListing.pblanc_no &&
              result.model_no === selectedListing.model_no &&
              result.house_type === selectedListing.house_type &&
              result.reside_secd === selectedListing.reside_secd &&
              result.subscription_rank_code === selectedListing.subscription_rank_code,
          )
        : mergedResults;

      setResults(filteredResults.length > 0 ? filteredResults : mergedResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "지원 판단에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-2xl font-bold">내 점수 기반 지원 판단</h2>
        <p className="mt-1 text-slate-500">선택한 공고를 기준으로 청약 가점을 계산하고 지원 등급을 산정합니다.</p>
      </section>

      <div className="grid gap-8 lg:grid-cols-5">
        <form onSubmit={run} className="card space-y-5 lg:col-span-2">
          <div className="rounded-lg border border-brand-100 bg-brand-50 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-brand-700">선택한 공고</p>
                {selectedApartmentName ? (
                  <>
                    <h3 className="mt-1 font-bold text-slate-950">{selectedApartmentName}</h3>
                    <p className="mt-1 text-sm text-slate-600">
                      {selectedListing.announcement_date || "공고일 미상"} · {selectedListing.house_type || "주택형 미상"}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {selectedListing.region_name} · {rankLabel(selectedListing.subscription_rank_code)} ·{" "}
                      {residenceLabel(selectedListing.reside_secd)}
                    </p>
                    <p className="mt-3 rounded-lg bg-white/70 p-3 text-xs leading-5 text-slate-600">
                      이 판단은 선택한 주택형, 공급순위, 거주구분 기준으로 계산됩니다.
                    </p>
                  </>
                ) : (
                  <p className="mt-1 text-sm text-slate-600">공고탐색에서 지원할 단지를 먼저 선택하세요.</p>
                )}
              </div>
              <Link to="/" className="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-brand-700 shadow-sm">
                변경
              </Link>
            </div>
          </div>

          <h3 className="font-semibold">사용자 조건</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">나이</label>
              <select className="input" value={scoreForm.age} onChange={(e) => updateScore("age", Number(e.target.value))}>
                {ageOptions.map((age) => (
                  <option key={age} value={age}>
                    만 {age}세
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">혼인 상태</label>
              <select className="input" value={scoreForm.marital_status} onChange={(e) => updateScore("marital_status", e.target.value)}>
                <option value="single">미혼</option>
                <option value="married">기혼</option>
              </select>
            </div>
            <div>
              <label className="label">무주택 여부</label>
              <select
                className="input"
                value={scoreForm.is_homeless ? "yes" : "no"}
                onChange={(e) => {
                  const isHomeless = e.target.value === "yes";
                  setScoreForm((current) => ({
                    ...current,
                    is_homeless: isHomeless,
                    homeless_years: isHomeless ? current.homeless_years : 0,
                  }));
                }}
              >
                <option value="yes">무주택</option>
                <option value="no">유주택</option>
              </select>
            </div>
            <div>
              <label className="label">무주택 기간</label>
              <select
                className="input"
                value={scoreForm.homeless_years}
                onChange={(e) => updateScore("homeless_years", Number(e.target.value))}
                disabled={!scoreForm.is_homeless}
              >
                {homelessYearOptions.map((year) => (
                  <option key={year} value={year}>
                    {yearLabel(year, 15)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">부양가족 수</label>
              <select className="input" value={scoreForm.dependents_count} onChange={(e) => updateScore("dependents_count", Number(e.target.value))}>
                {dependentOptions.map((count) => (
                  <option key={count} value={count}>
                    {dependentLabel(count)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">청약통장 가입연수</label>
              <select
                className="input"
                value={scoreForm.subscription_account_years}
                onChange={(e) => updateScore("subscription_account_years", Number(e.target.value))}
              >
                {accountYearOptions.map((year) => (
                  <option key={year} value={year}>
                    {yearLabel(year, 15)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">청약통장 추가 개월</label>
              <select
                className="input"
                value={scoreForm.subscription_account_months}
                onChange={(e) => updateScore("subscription_account_months", Number(e.target.value))}
              >
                {accountMonthOptions.map((month) => (
                  <option key={month} value={month}>
                    {month}개월
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 p-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
              <input type="checkbox" checked={isEligible} onChange={(e) => setIsEligible(e.target.checked)} />
              신청 자격을 충족합니다
            </label>
            {!isEligible && (
              <input
                className="input mt-3"
                placeholder="예: 청약통장 가입기간 미달"
                value={eligibilityReason}
                onChange={(e) => setEligibilityReason(e.target.value)}
              />
            )}
          </div>

          {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={loading || !selectedApartmentName}>
            {loading ? <Loader2 className="animate-spin" size={18} /> : "지원 판단 실행"}
          </button>
        </form>

        <div className="space-y-5 lg:col-span-3">
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-sm text-slate-500">계산된 청약 가점</p>
                <p className="mt-1 text-5xl font-bold text-brand-600">{score ? score.total_score : "-"}점</p>
              </div>
              {score && (
                <div className="grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
                  <span>무주택 {score.homeless_score}점</span>
                  <span>부양가족 {score.dependents_score}점</span>
                  <span>통장 {score.account_score}점</span>
                </div>
              )}
            </div>
            {score?.warnings.length ? (
              <div className="mt-4 flex gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                <AlertTriangle size={18} />
                <p>{score.warnings.join(" ")}</p>
              </div>
            ) : (
              <div className="mt-4 flex gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
                <CheckCircle2 size={18} />
                <p>입력값 기준으로 가점 계산이 완료됩니다.</p>
              </div>
            )}
          </div>

          {results.length === 0 ? (
            <div className="card flex min-h-64 items-center justify-center text-center text-slate-400">
              {selectedApartmentName ? "사용자 조건을 입력하고 지원 판단을 실행하세요." : "공고탐색에서 지원할 단지를 먼저 선택하세요."}
            </div>
          ) : (
            <div className="space-y-4">
              {results.map((result) => (
                <ResultCard
                  key={`${result.house_manage_no}-${result.model_no}-${result.house_type}-${result.reside_secd}-${result.subscription_rank_code}`}
                  result={result}
                />
              ))}
            </div>
          )}

          <div className="flex gap-2 rounded-lg bg-slate-100 p-4 text-sm text-slate-600">
            <ShieldAlert className="mt-0.5 shrink-0" size={18} />
            <p>예측 결과는 참고용입니다. 실제 신청 전에는 입주자모집공고의 자격, 거주요건, 공급유형을 반드시 확인해야 합니다.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
