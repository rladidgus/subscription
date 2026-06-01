from functools import lru_cache

import pandas as pd

from app.schemas.prediction import (
    ApplyHomeCandidateFilter,
    ApplyHomeClassificationRequest,
    ApplyHomeClassificationResponse,
    ApplyHomeClassifiedResult,
    ApplyHomePredictionRequest,
    ApplyHomePredictionResponse,
    ApplyHomePredictionResult,
    CutoffPredictionRequest,
    CutoffPredictionResponse,
)
from pipeline.common import PROJECT_ROOT
from pipeline.model_features import (
    find_applyhome_feature_rows,
    features_from_applyhome_row,
    features_from_prediction_request,
)


FINAL_MODEL_DIR = PROJECT_ROOT / "model_artifacts" / "final"
REGION_PERFORMANCE_PATH = PROJECT_ROOT / "model_artifacts" / "reports" / "region_performance.csv"
LGB_TUNED_MODEL_PATH = FINAL_MODEL_DIR / "lgb_tuned.txt"
HURDLE_MODEL_PATH = FINAL_MODEL_DIR / "hurdle_classifier.txt"
SEG_CLASSIFIER_MODEL_PATH = FINAL_MODEL_DIR / "seg_classifier_30.txt"
SEG_LOW_MODEL_PATH = FINAL_MODEL_DIR / "seg_model_low.txt"
SEG_HIGH_MODEL_PATH = FINAL_MODEL_DIR / "seg_model_high.txt"


@lru_cache(maxsize=1)
def _load_lightgbm_models():
    if not LGB_TUNED_MODEL_PATH.exists():
        return None
    try:
        import lightgbm as lgb
    except ImportError:
        return None

    models = {"regressor": lgb.Booster(model_file=str(LGB_TUNED_MODEL_PATH))}
    if HURDLE_MODEL_PATH.exists():
        models["hurdle"] = lgb.Booster(model_file=str(HURDLE_MODEL_PATH))
    if all(path.exists() for path in [SEG_CLASSIFIER_MODEL_PATH, SEG_LOW_MODEL_PATH, SEG_HIGH_MODEL_PATH]):
        models["segment_classifier"] = lgb.Booster(model_file=str(SEG_CLASSIFIER_MODEL_PATH))
        models["segment_low"] = lgb.Booster(model_file=str(SEG_LOW_MODEL_PATH))
        models["segment_high"] = lgb.Booster(model_file=str(SEG_HIGH_MODEL_PATH))
    return models


@lru_cache(maxsize=1)
def _load_region_performance() -> dict[str, dict]:
    if not REGION_PERFORMANCE_PATH.exists():
        return {}
    report = pd.read_csv(REGION_PERFORMANCE_PATH)
    return {str(row["region_code"]): row.to_dict() for _, row in report.iterrows()}


def _region_performance_fields(region_code: object) -> dict[str, object]:
    region = _load_region_performance().get(str(region_code))
    if not region:
        return {
            "region_mae": None,
            "region_confidence_level": None,
            "region_confidence_label": None,
        }
    return {
        "region_mae": round(float(region.get("best_mae_all")), 4) if pd.notna(region.get("best_mae_all")) else None,
        "region_confidence_level": region.get("confidence_level"),
        "region_confidence_label": region.get("confidence_label"),
    }


def _fallback_predict_cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    baseline = 45.0
    regional_adjustment = 3.0 if request.region_code.startswith("11") else 0.0
    competition_adjustment = min(request.competition_rate / 10, 8)
    predicted = min(max(baseline + regional_adjustment + competition_adjustment, 0), 84)
    return CutoffPredictionResponse(
        apartment_name=request.apartment_name,
        predicted_cutoff_score=round(predicted, 1),
        model_name="baseline-fallback",
        confidence_note="학습 모델을 사용할 수 없을 때 사용하는 임시 규칙 기반 예측값입니다.",
    )


def _predict_segment_soft(models: dict, features: pd.DataFrame) -> float:
    classifier = models.get("segment_classifier")
    low_model = models.get("segment_low")
    high_model = models.get("segment_high")
    if classifier is None or low_model is None or high_model is None:
        return float(models["regressor"].predict(features)[0])

    high_probability = classifier.predict(features)
    if getattr(high_probability, "ndim", 1) > 1:
        high_probability = high_probability[:, -1]
    high_probability_value = float(high_probability[0])
    low_prediction = float(low_model.predict(features)[0])
    high_prediction = float(high_model.predict(features)[0])
    return high_probability_value * high_prediction + (1 - high_probability_value) * low_prediction


def _predict_from_features(features: pd.DataFrame) -> tuple[float, str, str, float | None, float | None]:
    models = _load_lightgbm_models()
    if models is None:
        raise RuntimeError("LightGBM 모델을 사용할 수 없습니다.")

    hurdle = models.get("hurdle")
    if hurdle is not None:
        competition_probability = float(hurdle.predict(features)[0])
        shortage_probability = 1 - competition_probability
        if competition_probability < 0.5:
            return 0.0, "LightGBM-Hybrid", "shortage_or_zero", shortage_probability, competition_probability
        return (
            _predict_segment_soft(models, features),
            "LightGBM-Hybrid",
            "segment_soft",
            shortage_probability,
            competition_probability,
        )
    return float(models["regressor"].predict(features)[0]), "LightGBM-Tuned", "regression", None, None


def _clip_score(score: float) -> float:
    return min(max(score, 0), 84)


def predict_cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    models = _load_lightgbm_models()
    if models is None:
        return _fallback_predict_cutoff(request)

    try:
        features = features_from_prediction_request(request)
        predicted, model_name, _, _, _ = _predict_from_features(features)
    except (RuntimeError, ValueError, KeyError, TypeError):
        return _fallback_predict_cutoff(request)

    predicted = _clip_score(predicted)
    return CutoffPredictionResponse(
        apartment_name=request.apartment_name,
        predicted_cutoff_score=round(predicted, 1),
        model_name=model_name,
        confidence_note="ApplyHome 원천 데이터 기반 22개 피처를 LightGBM 모델에 입력해 계산한 예측값입니다.",
    )


def _row_to_prediction_result(row: pd.Series) -> ApplyHomePredictionResult:
    predicted, model_name, prediction_status, shortage_probability, competition_probability = _predict_from_features(
        features_from_applyhome_row(row)
    )
    actual_score = pd.to_numeric(row.get("LWET_SCORE"), errors="coerce")
    return ApplyHomePredictionResult(
        apartment_name=str(row["HOUSE_NM"]),
        house_manage_no=str(row["HOUSE_MANAGE_NO"]),
        pblanc_no=str(row["PBLANC_NO"]),
        model_no=str(row["MODEL_NO"]).zfill(2),
        house_type=str(row["HOUSE_TY"]),
        region_code=str(row["region_code"]),
        announcement_date=None if pd.isna(row.get("announcement_date")) else str(row.get("announcement_date")),
        reside_secd=str(row["RESIDE_SECD"]).zfill(2),
        subscription_rank_code=str(row["SUBSCRPT_RANK_CODE"]),
        predicted_cutoff_score=round(_clip_score(predicted), 1),
        actual_cutoff_score=None if pd.isna(actual_score) else round(float(actual_score), 1),
        model_name=model_name,
        prediction_status=prediction_status,
        shortage_probability=None if shortage_probability is None else round(shortage_probability, 4),
        competition_probability=None if competition_probability is None else round(competition_probability, 4),
        **_region_performance_fields(row["region_code"]),
        confidence_note="ApplyHome 실제 공고 행의 22개 피처를 그대로 사용한 예측값입니다.",
    )


def _row_to_not_eligible_result(row: pd.Series, reasons: list[str]) -> ApplyHomePredictionResult:
    actual_score = pd.to_numeric(row.get("LWET_SCORE"), errors="coerce")
    return ApplyHomePredictionResult(
        apartment_name=str(row["HOUSE_NM"]),
        house_manage_no=str(row["HOUSE_MANAGE_NO"]),
        pblanc_no=str(row["PBLANC_NO"]),
        model_no=str(row["MODEL_NO"]).zfill(2),
        house_type=str(row["HOUSE_TY"]),
        region_code=str(row["region_code"]),
        announcement_date=None if pd.isna(row.get("announcement_date")) else str(row.get("announcement_date")),
        reside_secd=str(row["RESIDE_SECD"]).zfill(2),
        subscription_rank_code=str(row["SUBSCRPT_RANK_CODE"]),
        predicted_cutoff_score=None,
        actual_cutoff_score=None if pd.isna(actual_score) else round(float(actual_score), 1),
        model_name="rule-based-eligibility-filter",
        prediction_status="not_eligible",
        **_region_performance_fields(row["region_code"]),
        confidence_note="; ".join(reasons) if reasons else "자격 필터에서 제외되어 모델 예측을 실행하지 않았습니다.",
    )


def _rows_from_filter(candidate: ApplyHomeCandidateFilter, limit: int = 20) -> pd.DataFrame:
    return find_applyhome_feature_rows(
        apartment_name=candidate.apartment_name,
        region_code=candidate.region_code,
        house_manage_no=candidate.house_manage_no,
        pblanc_no=candidate.pblanc_no,
        model_no=candidate.model_no,
        house_type=candidate.house_type,
        reside_secd=candidate.reside_secd,
        subscription_rank_code=candidate.subscription_rank_code,
        limit=limit,
    )


def predict_applyhome_cutoff(request: ApplyHomePredictionRequest) -> ApplyHomePredictionResponse:
    rows = find_applyhome_feature_rows(
        apartment_name=request.apartment_name,
        region_code=request.region_code,
        house_manage_no=request.house_manage_no,
        pblanc_no=request.pblanc_no,
        model_no=request.model_no,
        house_type=request.house_type,
        reside_secd=request.reside_secd,
        subscription_rank_code=request.subscription_rank_code,
        limit=request.limit,
    )
    return ApplyHomePredictionResponse(results=[_row_to_prediction_result(row) for _, row in rows.iterrows()])


def _classify_prediction(
    result: ApplyHomePredictionResult,
    user_score: float,
    margin: float,
    eligibility_reasons: list[str] | None = None,
) -> ApplyHomeClassifiedResult:
    eligibility_reasons = eligibility_reasons or []
    if result.prediction_status == "not_eligible":
        return ApplyHomeClassifiedResult(
            **result.model_dump(),
            user_score=user_score,
            score_gap=None,
            category="not_eligible",
            category_label="신청 불가",
            support_level="not_eligible",
            support_label="신청 불가",
            support_note="자격 요건을 충족하지 않아 모델 예측 전에 제외했습니다.",
            eligibility_status="ineligible",
            eligibility_reasons=eligibility_reasons,
        )

    if result.prediction_status == "shortage_or_zero":
        score_gap = None if result.predicted_cutoff_score is None else round(user_score - result.predicted_cutoff_score, 1)
        category = "available_now"
        category_label = "미달 가능"
        support_level = "opportunity"
        support_label = "미달 가능"
        support_note = "모델이 미달 또는 0점 가능성을 높게 봅니다. 자격 요건을 충족한다면 점수 부담은 낮은 편입니다."
    else:
        score_gap = None if result.predicted_cutoff_score is None else round(user_score - result.predicted_cutoff_score, 1)
        uncertainty = result.region_mae if result.region_mae is not None else margin
        if score_gap is not None and score_gap >= uncertainty * 2:
            category = "available_now"
            category_label = "지원 최적"
            support_level = "optimal"
            support_label = "지원 최적"
            support_note = (
                f"점수 여유가 +{score_gap}점으로, 이 지역 평균 오차 약 {round(uncertainty, 1)}점의 두 배 이상입니다."
            )
        elif score_gap is not None and score_gap >= uncertainty:
            category = "available_now"
            category_label = "안전권"
            support_level = "safe"
            support_label = "안전권"
            support_note = f"점수 여유가 +{score_gap}점으로, 이 지역 평균 오차 약 {round(uncertainty, 1)}점을 넘어섭니다."
        elif score_gap is not None and score_gap >= 0:
            category = "prepare_later"
            category_label = "가능하지만 불안"
            support_level = "uncertain"
            support_label = "가능하지만 불안"
            support_note = (
                f"예측 커트라인보다 {score_gap}점 높지만, 이 지역 평균 오차 약 {round(uncertainty, 1)}점 안쪽입니다."
            )
        elif score_gap is not None and score_gap >= -uncertainty:
            category = "prepare_later"
            category_label = "상향 도전"
            support_level = "stretch"
            support_label = "상향 도전"
            support_note = (
                f"예측 커트라인보다 {abs(score_gap)}점 낮지만, 이 지역 평균 오차 약 {round(uncertainty, 1)}점 범위 안입니다."
            )
        else:
            category = "difficult"
            category_label = "어려움"
            support_level = "difficult"
            support_label = "어려움"
            support_note = (
                "예측 커트라인과의 차이가 지역 평균 오차 범위를 넘어, 현재 점수로는 보수적으로 보는 편이 좋습니다."
            )

    return ApplyHomeClassifiedResult(
        **result.model_dump(),
        user_score=user_score,
        score_gap=score_gap,
        category=category,
        category_label=category_label,
        support_level=support_level,
        support_label=support_label,
        support_note=support_note,
        eligibility_status="eligible",
        eligibility_reasons=[],
    )


def classify_applyhome_candidates(request: ApplyHomeClassificationRequest) -> ApplyHomeClassificationResponse:
    filters = request.candidates
    if not filters and request.apartment_name:
        filters = [ApplyHomeCandidateFilter(apartment_name=request.apartment_name)]

    prediction_results: list[ApplyHomePredictionResult] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for candidate in filters:
        rows = _rows_from_filter(candidate, request.limit)
        for _, row in rows.iterrows():
            key = (
                str(row["HOUSE_MANAGE_NO"]),
                str(row["PBLANC_NO"]),
                str(row["MODEL_NO"]),
                str(row["HOUSE_TY"]),
                str(row["RESIDE_SECD"]),
                str(row["SUBSCRPT_RANK_CODE"]),
            )
            if key in seen:
                continue
            seen.add(key)
            if request.is_eligible:
                prediction_results.append(_row_to_prediction_result(row))
            else:
                reasons = request.eligibility_reasons or ["사용자 자격 필터에서 제외되었습니다."]
                prediction_results.append(_row_to_not_eligible_result(row, reasons))

    classified = [
        _classify_prediction(result, request.user_score, request.margin, request.eligibility_reasons)
        for result in prediction_results
    ]
    return ApplyHomeClassificationResponse(
        available_now=[result for result in classified if result.category == "available_now"],
        prepare_later=[result for result in classified if result.category == "prepare_later"],
        difficult=[result for result in classified if result.category == "difficult"],
        not_eligible=[result for result in classified if result.category == "not_eligible"],
    )
