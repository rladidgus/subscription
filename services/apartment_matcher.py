from app.schemas.apartment import ApartmentMatchRequest, ApartmentMatchResponse, MatchedApartment


def _with_gap(apartment, score: int) -> MatchedApartment:
    return MatchedApartment(**apartment.model_dump(), score_gap=round(apartment.predicted_cutoff_score - score, 1))


def match_apartments(request: ApartmentMatchRequest) -> ApartmentMatchResponse:
    available_now: list[MatchedApartment] = []
    prepare_later: list[MatchedApartment] = []
    difficult: list[MatchedApartment] = []

    for apartment in request.apartments:
        if request.current_score >= apartment.predicted_cutoff_score:
            available_now.append(_with_gap(apartment, request.current_score))
        elif request.future_score >= apartment.predicted_cutoff_score:
            prepare_later.append(_with_gap(apartment, request.current_score))
        else:
            difficult.append(_with_gap(apartment, request.future_score))

    return ApartmentMatchResponse(
        available_now=available_now,
        prepare_later=prepare_later,
        difficult=difficult,
    )
