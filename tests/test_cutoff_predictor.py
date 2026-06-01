from app.schemas.prediction import ApplyHomeClassificationRequest, ApplyHomePredictionRequest, CutoffPredictionRequest
from pipeline.model_features import MODEL_FEATURE_COLUMNS, features_from_prediction_request
from services.cutoff_predictor import classify_applyhome_candidates, predict_applyhome_cutoff, predict_cutoff


def _prediction_request() -> CutoffPredictionRequest:
    return CutoffPredictionRequest(
        apartment_name="샘플 아파트",
        region_code="11",
        general_supply_units=120,
        sale_price=750000000,
        competition_rate=24.5,
        housing_price_index=103.2,
        supply_year=2026,
        supply_quarter=2,
        area_m2=84,
    )


def test_predict_cutoff_returns_score_range():
    response = predict_cutoff(_prediction_request())
    assert 0 <= response.predicted_cutoff_score <= 84


def test_features_from_prediction_request_matches_model_schema(monkeypatch):
    monkeypatch.setattr(
        "pipeline.model_features._feature_stats",
        lambda: {
            "global_score": 45.0,
            "global_score_std": 5.0,
            "price_by_region": {},
            "cmpet_by_region": {},
            "region_scores": {},
        },
    )

    features = features_from_prediction_request(_prediction_request())

    assert list(features.columns) == MODEL_FEATURE_COLUMNS
    assert features.loc[0, "notice_year"] == 2026
    assert features.loc[0, "notice_month"] == 6


def test_predict_applyhome_cutoff_uses_real_feature_rows():
    response = predict_applyhome_cutoff(
        ApplyHomePredictionRequest(apartment_name="골드클래스 시그니처", limit=1)
    )

    assert len(response.results) == 1
    result = response.results[0]
    assert result.apartment_name == "골드클래스 시그니처"
    assert 0 <= result.predicted_cutoff_score <= 84
    assert result.model_name == "LightGBM-Hybrid"
    assert result.prediction_status in {"segment_soft", "shortage_or_zero"}


def test_classify_applyhome_candidates_groups_by_user_score():
    response = classify_applyhome_candidates(
        ApplyHomeClassificationRequest(
            user_score=50,
            apartment_name="골드클래스 시그니처",
            limit=1,
        )
    )

    total = len(response.available_now) + len(response.prepare_later) + len(response.difficult)
    assert total == 1
    assert response.available_now[0].category_label == "지원 최적"
    assert response.available_now[0].support_level == "optimal"
    assert response.available_now[0].region_mae is not None


def test_classify_applyhome_candidates_skips_model_when_user_is_ineligible():
    response = classify_applyhome_candidates(
        ApplyHomeClassificationRequest(
            user_score=50,
            apartment_name="골드클래스 시그니처",
            is_eligible=False,
            eligibility_reasons=["청약통장 가입기간 미달"],
            limit=1,
        )
    )

    assert len(response.not_eligible) == 1
    result = response.not_eligible[0]
    assert result.predicted_cutoff_score is None
    assert result.model_name == "rule-based-eligibility-filter"
    assert result.category_label == "신청 불가"
    assert result.support_level == "not_eligible"
    assert result.eligibility_reasons == ["청약통장 가입기간 미달"]


def test_classify_applyhome_candidates_marks_uncertain_when_gap_is_inside_region_error():
    response = classify_applyhome_candidates(
        ApplyHomeClassificationRequest(
            user_score=35,
            apartment_name="골드클래스 시그니처",
            limit=1,
        )
    )

    assert len(response.prepare_later) == 1
    result = response.prepare_later[0]
    assert result.category_label == "가능하지만 불안"
    assert result.support_level == "uncertain"
    assert "지역 평균 오차" in result.support_note
