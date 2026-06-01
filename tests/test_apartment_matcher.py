from app.schemas.apartment import ApartmentMatchRequest, ApartmentPrediction
from services.apartment_matcher import match_apartments


def test_match_apartments_splits_by_score():
    response = match_apartments(
        ApartmentMatchRequest(
            current_score=42,
            future_score=50,
            apartments=[
                ApartmentPrediction(
                    apartment_id="apt-001",
                    apartment_name="샘플 아파트",
                    region_name="서울",
                    predicted_cutoff_score=47.2,
                )
            ],
        )
    )
    assert len(response.prepare_later) == 1
