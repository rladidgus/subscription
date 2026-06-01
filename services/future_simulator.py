from app.schemas.score import ScoreRequest, ScoreSimulationRequest, ScoreSimulationResponse
from services.score_calculator import calculate_score


def simulate_future_score(request: ScoreSimulationRequest) -> ScoreSimulationResponse:
    current = calculate_score(request.user)
    future_user_data = request.user.model_dump()
    future_user_data["homeless_years"] = (
        request.user.homeless_years + request.years_later
        if request.user.is_homeless
        else request.user.homeless_years
    )
    future_user_data["subscription_account_years"] = request.user.subscription_account_years + request.years_later
    total_account_months = (
        future_user_data["subscription_account_years"] * 12
        + future_user_data["subscription_account_months"]
    )
    future_user_data["subscription_account_years"] = total_account_months // 12
    future_user_data["subscription_account_months"] = total_account_months % 12
    future_user = ScoreRequest(**future_user_data)
    future = calculate_score(future_user)
    return ScoreSimulationResponse(
        current_score=current.total_score,
        future_score=future.total_score,
        years_later=request.years_later,
    )
