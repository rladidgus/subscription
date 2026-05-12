from pydantic import BaseModel, Field


class StrategyRequest(BaseModel):
    current_score: int = Field(ge=0)
    future_score: int = Field(ge=0)
    years_later: int = Field(ge=0)
    available_now_count: int = Field(ge=0)
    prepare_later_count: int = Field(ge=0)
    preferred_regions: list[str] = []


class StrategyResponse(BaseModel):
    strategy_text: str
