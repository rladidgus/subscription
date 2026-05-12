from app.schemas.score import ScoreRequest
from services.score_calculator import calculate_score


def test_calculate_score_returns_total_score():
    response = calculate_score(
        ScoreRequest(
            age=35,
            is_homeless=True,
            homeless_years=3,
            dependents_count=1,
            subscription_account_years=4,
            marital_status="single",
        )
    )
    assert response.total_score >= 0


def test_calculate_score_uses_subscription_score_table():
    response = calculate_score(
        ScoreRequest(
            age=35,
            is_homeless=True,
            homeless_years=3,
            dependents_count=1,
            subscription_account_years=4,
        )
    )

    assert response.homeless_score == 8
    assert response.dependents_score == 10
    assert response.account_score == 6
    assert response.total_score == 24


def test_under_30_single_homeless_score_is_zero():
    response = calculate_score(
        ScoreRequest(
            age=29,
            is_homeless=True,
            homeless_years=3,
            dependents_count=1,
            subscription_account_years=4,
            marital_status="single",
        )
    )

    assert response.homeless_score == 0
    assert "만 30세 미만 미혼 무주택자는 무주택기간 가점이 0점입니다." in response.warnings


def test_account_score_handles_month_boundary():
    less_than_six_months = calculate_score(
        ScoreRequest(
            age=35,
            is_homeless=True,
            homeless_years=0,
            dependents_count=0,
            subscription_account_years=0,
            subscription_account_months=5,
        )
    )
    six_months = calculate_score(
        ScoreRequest(
            age=35,
            is_homeless=True,
            homeless_years=0,
            dependents_count=0,
            subscription_account_years=0,
            subscription_account_months=6,
        )
    )

    assert less_than_six_months.account_score == 1
    assert six_months.account_score == 2
