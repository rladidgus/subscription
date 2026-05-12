from fastapi import APIRouter

from app.schemas.strategy import StrategyRequest, StrategyResponse
from services.strategy_generator import generate_strategy


router = APIRouter()


@router.post("/generate", response_model=StrategyResponse)
def strategy(request: StrategyRequest) -> StrategyResponse:
    return generate_strategy(request)
