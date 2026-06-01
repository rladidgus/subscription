from pydantic import BaseModel, Field


class ScoreRequest(BaseModel):
    age: int = Field(ge=0)
    is_homeless: bool
    homeless_years: int = Field(ge=0)
    dependents_count: int = Field(ge=0)
    subscription_account_years: int = Field(ge=0)
    subscription_account_months: int = Field(default=0, ge=0, le=11)
    marital_status: str = "single"


class ScoreResponse(BaseModel):
    total_score: int
    homeless_score: int
    dependents_score: int
    account_score: int
    warnings: list[str] = []


class ScoreSimulationRequest(BaseModel):
    user: ScoreRequest
    years_later: int = Field(ge=0)


class ScoreSimulationResponse(BaseModel):
    current_score: int
    future_score: int
    years_later: int
