from app.schemas.prediction import CutoffPredictionRequest
from services.cutoff_predictor import predict_cutoff


def test_predict_cutoff_returns_score_range():
    response = predict_cutoff(
        CutoffPredictionRequest(
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
    )
    assert 0 <= response.predicted_cutoff_score <= 84
