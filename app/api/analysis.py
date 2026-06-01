from fastapi import APIRouter

from app.schemas.analysis import AnalysisRequest, AnalysisResponse, to_apartment_prediction
from app.schemas.apartment import ApartmentMatchRequest
from app.schemas.score import ScoreSimulationRequest
from app.schemas.strategy import StrategyRequest
from app.db.repository import list_sample_apartment_predictions
from services.apartment_matcher import match_apartments
from services.cutoff_predictor import predict_cutoff
from services.future_simulator import simulate_future_score
from services.strategy_generator import generate_strategy


router = APIRouter()


@router.post("/run", response_model=AnalysisResponse)
def run_analysis(request: AnalysisRequest) -> AnalysisResponse:
    score_result = simulate_future_score(
        ScoreSimulationRequest(user=request.user, years_later=request.years_later)
    )
    used_sample_apartments = not request.apartments
    if used_sample_apartments:
        predictions = []
        apartment_predictions = list_sample_apartment_predictions()
    else:
        predictions = [predict_cutoff(apartment) for apartment in request.apartments]
        apartment_predictions = [
            to_apartment_prediction(apartment, prediction, index)
            for index, (apartment, prediction) in enumerate(zip(request.apartments, predictions))
        ]
    matched = match_apartments(
        ApartmentMatchRequest(
            current_score=score_result.current_score,
            future_score=score_result.future_score,
            apartments=apartment_predictions,
        )
    )
    strategy = generate_strategy(
        StrategyRequest(
            current_score=score_result.current_score,
            future_score=score_result.future_score,
            years_later=request.years_later,
            available_now_count=len(matched.available_now),
            prepare_later_count=len(matched.prepare_later),
            preferred_regions=request.preferred_regions,
        )
    )
    return AnalysisResponse(
        current_score=score_result.current_score,
        future_score=score_result.future_score,
        years_later=request.years_later,
        predictions=predictions,
        matched_apartments=matched,
        used_sample_apartments=used_sample_apartments,
        strategy_text=strategy.strategy_text,
    )
