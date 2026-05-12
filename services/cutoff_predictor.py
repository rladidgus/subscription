from app.schemas.prediction import CutoffPredictionRequest, CutoffPredictionResponse


def predict_cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    baseline = 45.0
    regional_adjustment = 3.0 if request.region_code.startswith("11") else 0.0
    competition_adjustment = min(request.competition_rate / 10, 8)
    predicted = min(max(baseline + regional_adjustment + competition_adjustment, 0), 84)
    return CutoffPredictionResponse(
        apartment_name=request.apartment_name,
        predicted_cutoff_score=round(predicted, 1),
        model_name="baseline-fallback",
        confidence_note="학습 모델이 없을 때 사용하는 임시 규칙 기반 예측값입니다.",
    )
