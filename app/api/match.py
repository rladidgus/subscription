from fastapi import APIRouter

from app.schemas.apartment import ApartmentMatchRequest, ApartmentMatchResponse
from services.apartment_matcher import match_apartments


router = APIRouter()


@router.post("/apartments", response_model=ApartmentMatchResponse)
def apartments(request: ApartmentMatchRequest) -> ApartmentMatchResponse:
    return match_apartments(request)
