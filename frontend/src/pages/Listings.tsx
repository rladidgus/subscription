import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import { api, type ApplyHomeListing } from "../api";
import { rankLabel, residenceLabel } from "../applyHomeLabels";
import { getRegionLabel, regionOptions } from "../regions";

function listingParams(listing: ApplyHomeListing) {
  const params = new URLSearchParams({
    apartment_name: listing.apartment_name,
    house_manage_no: listing.house_manage_no,
    pblanc_no: listing.pblanc_no,
    model_no: listing.model_no,
    house_type: listing.house_type,
    region_code: listing.region_code,
    region_name: getRegionLabel(listing.region_code),
    reside_secd: listing.reside_secd,
    subscription_rank_code: listing.subscription_rank_code,
  });

  if (listing.announcement_date) {
    params.set("announcement_date", listing.announcement_date);
  }

  return params.toString();
}

function cutoffLabel(score: number | null) {
  if (score == null) {
    return "-";
  }
  return score <= 0 ? "미달 가능" : `${score}점`;
}

function ListingCard({ listing, onSelect }: { listing: ApplyHomeListing; onSelect: () => void }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs text-slate-500">{listing.announcement_date ?? "공고일 미상"} · {listing.house_type}</p>
          <h3 className="mt-1 text-lg font-bold text-slate-950">{listing.apartment_name}</h3>
          <p className="mt-1 text-sm text-slate-500">
            {getRegionLabel(listing.region_code)} · {rankLabel(listing.subscription_rank_code)} · {residenceLabel(listing.reside_secd)}
          </p>
        </div>
        <button type="button" onClick={onSelect} className="btn-primary shrink-0 gap-2">
          선택
          <ArrowRight size={16} />
        </button>
      </div>

      <div className="mt-4 border-t border-slate-100 pt-4 text-sm">
        <div>
          <p className="text-xs text-slate-400">예측 커트라인</p>
          <p className="font-semibold text-slate-900">{cutoffLabel(listing.predicted_cutoff_score)}</p>
        </div>
      </div>
    </article>
  );
}

export default function Listings() {
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("");
  const [listings, setListings] = useState<ApplyHomeListing[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadListings = async (nextKeyword = keyword, nextRegion = selectedRegion) => {
    setLoading(true);
    setError("");

    try {
      const response = await api.predictApplyHome({
        apartment_name: nextKeyword.trim() || undefined,
        region_code: nextRegion || undefined,
        limit: 100,
      });
      setListings(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "공고를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const search = async (event?: FormEvent) => {
    event?.preventDefault();
    await loadListings();
  };

  const changeRegion = (regionCode: string) => {
    setSelectedRegion(regionCode);
    void loadListings(keyword, regionCode);
  };

  useEffect(() => {
    void loadListings("", "");
  }, []);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h2 className="text-2xl font-bold">공고탐색</h2>
        <p className="text-slate-500">실제 청약 공고를 먼저 고른 뒤, 선택한 단지 기준으로 내 청약 조건을 입력합니다.</p>
      </section>

      <form onSubmit={search} className="card">
        <label className="label">단지명 검색</label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="flex-1">
            <input
              className="input"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="단지명을 입력하지 않으면 선택한 지역 전체를 검색합니다"
            />
          </div>
          <button type="submit" className="btn-primary gap-2" disabled={loading}>
            {loading && <Loader2 className="animate-spin" size={18} />}
            검색
          </button>
        </div>
        <div className="mt-4">
          <label className="label">지역 선택</label>
          <select className="input" value={selectedRegion} onChange={(event) => changeRegion(event.target.value)}>
            {regionOptions.map((region) => (
              <option key={region.value || "all"} value={region.value}>
                {region.label}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="mt-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      </form>

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-semibold">검색 결과</h3>
          <p className="text-sm text-slate-500">{listings.length}개</p>
        </div>

        {loading ? (
          <div className="card flex min-h-48 items-center justify-center gap-2 text-slate-500">
            <Loader2 className="animate-spin" size={18} />
            공고를 불러오는 중입니다.
          </div>
        ) : listings.length === 0 ? (
          <div className="card flex min-h-48 items-center justify-center text-center text-slate-400">
            검색된 공고가 없습니다.
          </div>
        ) : (
          <div className="grid gap-4">
            {listings.map((listing) => (
              <ListingCard
                key={`${listing.house_manage_no}-${listing.pblanc_no}-${listing.model_no}-${listing.house_type}-${listing.reside_secd}-${listing.subscription_rank_code}`}
                listing={listing}
                onSelect={() => navigate(`/predict?${listingParams(listing)}`)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
