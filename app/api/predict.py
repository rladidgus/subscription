from fastapi import APIRouter

from app.schemas.prediction import CutoffPredictionRequest, CutoffPredictionResponse
from services.cutoff_predictor import predict_cutoff


router = APIRouter()


@router.post("/cutoff", response_model=CutoffPredictionResponse)
def cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    return predict_cutoff(request)
