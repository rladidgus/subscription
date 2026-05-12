from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_analysis_returns_scores_matches_and_strategy():
    response = client.post(
        "/analysis/run",
        json={
            "user": {
                "age": 35,
                "is_homeless": True,
                "homeless_years": 3,
                "dependents_count": 1,
                "subscription_account_years": 4,
                "subscription_account_months": 0,
                "marital_status": "single",
            },
            "years_later": 3,
            "preferred_regions": ["서울", "경기"],
            "apartments": [
                {
                    "apartment_name": "샘플 아파트",
                    "region_code": "11",
                    "general_supply_units": 120,
                    "sale_price": 750000000,
                    "competition_rate": 24.5,
                    "housing_price_index": 103.2,
                    "supply_year": 2026,
                    "supply_quarter": 2,
                    "area_m2": 84,
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_score"] == 24
    assert body["future_score"] >= body["current_score"]
    assert len(body["predictions"]) == 1
    assert body["used_sample_apartments"] is False
    assert "matched_apartments" in body
    assert body["strategy_text"]


def test_run_analysis_uses_sample_apartments_when_request_has_no_apartments():
    response = client.post(
        "/analysis/run",
        json={
            "user": {
                "age": 35,
                "is_homeless": True,
                "homeless_years": 3,
                "dependents_count": 1,
                "subscription_account_years": 4,
            },
            "years_later": 3,
            "apartments": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["predictions"] == []
    assert body["used_sample_apartments"] is True
    total_matches = sum(len(body["matched_apartments"][key]) for key in ["available_now", "prepare_later", "difficult"])
    assert total_matches >= 20
