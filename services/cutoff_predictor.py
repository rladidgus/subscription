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
LGB_TUNED_MODEL_PATH = FINAL_MODEL_DIR / "lgb_tuned.txt"
HURDLE_MODEL_PATH = FINAL_MODEL_DIR / "hurdle_classifier.txt"


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
    return models


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


def _predict_from_features(features: pd.DataFrame) -> tuple[float, str]:
    models = _load_lightgbm_models()
    if models is None:
        raise RuntimeError("LightGBM 모델을 사용할 수 없습니다.")

    hurdle = models.get("hurdle")
    if hurdle is not None:
        win_probability = float(hurdle.predict(features)[0])
        if win_probability < 0.5:
            return 0.0, "LightGBM-Hurdle"
        return float(models["regressor"].predict(features)[0]), "LightGBM-Hurdle"
    return float(models["regressor"].predict(features)[0]), "LightGBM-Tuned"


def _clip_score(score: float) -> float:
    return min(max(score, 0), 84)


def predict_cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    models = _load_lightgbm_models()
    if models is None:
        return _fallback_predict_cutoff(request)

    try:
        features = features_from_prediction_request(request)
        predicted, model_name = _predict_from_features(features)
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
    predicted, model_name = _predict_from_features(features_from_applyhome_row(row))
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
        confidence_note="ApplyHome 실제 공고 행의 22개 피처를 그대로 사용한 예측값입니다.",
    )


def _rows_from_filter(candidate: ApplyHomeCandidateFilter, limit: int = 20) -> pd.DataFrame:
    return find_applyhome_feature_rows(
        apartment_name=candidate.apartment_name,
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
        house_manage_no=request.house_manage_no,
        pblanc_no=request.pblanc_no,
        model_no=request.model_no,
        house_type=request.house_type,
        reside_secd=request.reside_secd,
        subscription_rank_code=request.subscription_rank_code,
        limit=request.limit,
    )
    return ApplyHomePredictionResponse(results=[_row_to_prediction_result(row) for _, row in rows.iterrows()])


def _classify_prediction(result: ApplyHomePredictionResult, user_score: float, margin: float) -> ApplyHomeClassifiedResult:
    score_gap = round(user_score - result.predicted_cutoff_score, 1)
    if score_gap >= margin:
        category = "available_now"
        category_label = "지원 가능"
    elif score_gap >= -margin:
        category = "prepare_later"
        category_label = "준비 필요"
    else:
        category = "difficult"
        category_label = "어려움"

    return ApplyHomeClassifiedResult(
        **result.model_dump(),
        user_score=user_score,
        score_gap=score_gap,
        category=category,
        category_label=category_label,
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
            prediction_results.append(_row_to_prediction_result(row))

    classified = [_classify_prediction(result, request.user_score, request.margin) for result in prediction_results]
    return ApplyHomeClassificationResponse(
        available_now=[result for result in classified if result.category == "available_now"],
        prepare_later=[result for result in classified if result.category == "prepare_later"],
        difficult=[result for result in classified if result.category == "difficult"],
    )
