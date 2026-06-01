from app.schemas.strategy import StrategyRequest, StrategyResponse


def generate_strategy(request: StrategyRequest) -> StrategyResponse:
    regions = ", ".join(request.preferred_regions) if request.preferred_regions else "선호 지역"
    text = (
        f"현재 점수는 {request.current_score}점이고 "
        f"{request.years_later}년 후 예상 점수는 {request.future_score}점입니다. "
        f"{regions} 기준으로 지금 도전 가능한 단지는 {request.available_now_count}개, "
        f"추가 준비 후 검토할 단지는 {request.prepare_later_count}개입니다."
    )
    return StrategyResponse(strategy_text=text)
