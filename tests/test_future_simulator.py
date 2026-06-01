from app.schemas.score import ScoreRequest, ScoreSimulationRequest
from services.future_simulator import simulate_future_score


def test_simulate_future_score_increases_or_keeps_score():
    response = simulate_future_score(
        ScoreSimulationRequest(
            user=ScoreRequest(
                age=35,
                is_homeless=True,
                homeless_years=3,
                dependents_count=1,
                subscription_account_years=4,
            ),
            years_later=3,
        )
    )
    assert response.future_score >= response.current_score
