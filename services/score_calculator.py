from app.schemas.score import ScoreRequest, ScoreResponse

HOMELESS_MAX_YEARS = 15
HOMELESS_MAX_SCORE = 32
DEPENDENTS_MAX_COUNT = 6
DEPENDENTS_MAX_SCORE = 35
ACCOUNT_MAX_MONTHS = 15 * 12
ACCOUNT_MAX_SCORE = 17


def _homeless_score(years: int, is_homeless: bool) -> int:
    if not is_homeless:
        return 0
    if years >= HOMELESS_MAX_YEARS:
        return HOMELESS_MAX_SCORE
    return (years + 1) * 2


def _dependents_score(count: int) -> int:
    capped_count = min(count, DEPENDENTS_MAX_COUNT)
    return min((capped_count + 1) * 5, DEPENDENTS_MAX_SCORE)


def _account_score(years: int, months: int) -> int:
    total_months = years * 12 + months
    if total_months >= ACCOUNT_MAX_MONTHS:
        return ACCOUNT_MAX_SCORE
    if total_months < 6:
        return 1
    if total_months < 12:
        return 2
    full_years = total_months // 12
    return min(full_years + 2, ACCOUNT_MAX_SCORE)


def _is_single(marital_status: str) -> bool:
    return marital_status.lower() in {"single", "unmarried", "미혼"}


def _warnings(request: ScoreRequest) -> list[str]:
    warnings: list[str] = []
    if not request.is_homeless and request.homeless_years > 0:
        warnings.append("유주택자는 입력한 무주택기간을 점수에 반영하지 않습니다.")
    if request.is_homeless and request.age < 30 and _is_single(request.marital_status):
        warnings.append("만 30세 미만 미혼 무주택자는 무주택기간 가점이 0점입니다.")
    if request.dependents_count > DEPENDENTS_MAX_COUNT:
        warnings.append("부양가족수는 6명 이상부터 최대 35점으로 계산합니다.")
    if request.subscription_account_years >= 15:
        warnings.append("청약통장 가입기간은 15년 이상부터 최대 17점으로 계산합니다.")
    return warnings


def calculate_score(request: ScoreRequest) -> ScoreResponse:
    warnings = _warnings(request)
    is_under_30_single = request.age < 30 and _is_single(request.marital_status)
    homeless_score = 0 if request.is_homeless and is_under_30_single else _homeless_score(
        request.homeless_years,
        request.is_homeless,
    )
    dependents_score = _dependents_score(request.dependents_count)
    account_score = _account_score(
        request.subscription_account_years,
        request.subscription_account_months,
    )
    total_score = homeless_score + dependents_score + account_score

    if total_score > 84:
        warnings.append("청약 가점 상한 84점을 적용했습니다.")
        total_score = 84

    return ScoreResponse(
        total_score=total_score,
        homeless_score=homeless_score,
        dependents_score=dependents_score,
        account_score=account_score,
        warnings=warnings,
    )
