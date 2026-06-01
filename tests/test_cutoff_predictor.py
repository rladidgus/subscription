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
    assert result.model_name.startswith("LightGBM")


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
    assert response.available_now[0].category_label == "지원 가능"
