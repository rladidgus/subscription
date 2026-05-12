from pydantic import BaseModel


class ApartmentPrediction(BaseModel):
    apartment_id: str
    apartment_name: str
    region_name: str
    predicted_cutoff_score: float


class MatchedApartment(ApartmentPrediction):
    score_gap: float


class ApartmentMatchRequest(BaseModel):
    current_score: int
    future_score: int
    apartments: list[ApartmentPrediction]


class ApartmentMatchResponse(BaseModel):
    available_now: list[MatchedApartment]
    prepare_later: list[MatchedApartment]
    difficult: list[MatchedApartment]
