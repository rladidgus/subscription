from fastapi import APIRouter

from app.schemas.score import ScoreRequest, ScoreResponse, ScoreSimulationRequest, ScoreSimulationResponse
from services.future_simulator import simulate_future_score
from services.score_calculator import calculate_score


router = APIRouter()


@router.post("/calculate", response_model=ScoreResponse)
def calculate(request: ScoreRequest) -> ScoreResponse:
    return calculate_score(request)


@router.post("/simulate", response_model=ScoreSimulationResponse)
def simulate(request: ScoreSimulationRequest) -> ScoreSimulationResponse:
    return simulate_future_score(request)
