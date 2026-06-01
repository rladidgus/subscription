from pydantic import BaseModel, Field

from app.schemas.apartment import ApartmentMatchResponse, ApartmentPrediction
from app.schemas.prediction import CutoffPredictionRequest, CutoffPredictionResponse
from app.schemas.score import ScoreRequest


class AnalysisRequest(BaseModel):
    user: ScoreRequest
    years_later: int = Field(ge=0)
    apartments: list[CutoffPredictionRequest] = []
    preferred_regions: list[str] = []


class AnalysisResponse(BaseModel):
    current_score: int
    future_score: int
    years_later: int
    predictions: list[CutoffPredictionResponse]
    matched_apartments: ApartmentMatchResponse
    used_sample_apartments: bool
    strategy_text: str


def to_apartment_prediction(
    request: CutoffPredictionRequest,
    response: CutoffPredictionResponse,
    index: int,
) -> ApartmentPrediction:
    return ApartmentPrediction(
        apartment_id=f"apt-{index + 1:03d}",
        apartment_name=response.apartment_name,
        region_name=request.region_code,
        predicted_cutoff_score=response.predicted_cutoff_score,
    )
