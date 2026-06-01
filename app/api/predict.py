from fastapi import APIRouter

from app.schemas.prediction import (
    ApplyHomeClassificationRequest,
    ApplyHomeClassificationResponse,
    ApplyHomePredictionRequest,
    ApplyHomePredictionResponse,
    CutoffPredictionRequest,
    CutoffPredictionResponse,
)
from services.cutoff_predictor import classify_applyhome_candidates, predict_applyhome_cutoff, predict_cutoff


router = APIRouter()


@router.post("/cutoff", response_model=CutoffPredictionResponse)
def cutoff(request: CutoffPredictionRequest) -> CutoffPredictionResponse:
    return predict_cutoff(request)


@router.post("/applyhome-cutoff", response_model=ApplyHomePredictionResponse)
def applyhome_cutoff(request: ApplyHomePredictionRequest) -> ApplyHomePredictionResponse:
    return predict_applyhome_cutoff(request)


@router.post("/applyhome-classify", response_model=ApplyHomeClassificationResponse)
def applyhome_classify(request: ApplyHomeClassificationRequest) -> ApplyHomeClassificationResponse:
    return classify_applyhome_candidates(request)
