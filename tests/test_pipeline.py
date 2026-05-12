from pathlib import Path
from urllib.parse import quote

import pandas as pd
import pytest

from pipeline.build_features import build_features
from pipeline.collect_public_api import (
    _fetch_odcloud_rows,
    collect_competition_api,
    collect_public_api,
    collect_special_supply_api,
    parse_competition_rows,
    parse_public_api_rows,
    parse_special_supply_rows,
)
from pipeline.collect_rone import collect_rone
from pipeline.collect_subscription_pdf import (
    CutoffDataError,
    MANUAL_CUTOFF_PATH,
    MANUAL_CUTOFF_TEMPLATE_PATH,
    _normalize_manual_cutoffs,
    collect_subscription_pdf,
    create_manual_cutoff_template,
    create_manual_cutoff_template_from_public_supply,
    promote_manual_cutoff_template,
)
from pipeline.common import TRAINING_COLUMNS
from pipeline.preprocess import preprocess


def test_collectors_create_raw_csv_files():
    paths = [
        collect_public_api(),
        collect_competition_api(),
        collect_special_supply_api(),
        collect_subscription_pdf(),
        collect_rone(),
    ]

    for path in paths:
        assert isinstance(path, Path)
        assert path.exists()


def test_create_manual_cutoff_template_creates_editable_csv():
    path = create_manual_cutoff_template()
    df = pd.read_csv(path)

    assert path.exists()
    assert {"apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"}.issubset(df.columns)


def test_create_manual_cutoff_template_from_public_supply_creates_blank_cutoff_template():
    path = create_manual_cutoff_template_from_public_supply(overwrite=True)
    df = pd.read_csv(path)

    assert path.exists()
    assert list(df.columns) == ["apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"]
    assert "apartment_id" in df.columns


def test_collect_subscription_pdf_normalizes_manual_cutoff_csv():
    path = collect_subscription_pdf()
    df = pd.read_csv(path)

    assert path.exists()
    assert list(df.columns) == ["apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"]
    assert df["cutoff_score"].between(0, 84).all()


def test_promote_manual_cutoff_template_uses_filled_template():
    original = pd.read_csv(MANUAL_CUTOFF_TEMPLATE_PATH) if MANUAL_CUTOFF_TEMPLATE_PATH.exists() else None
    original_manual = pd.read_csv(MANUAL_CUTOFF_PATH) if MANUAL_CUTOFF_PATH.exists() else None
    try:
        df = pd.DataFrame(
            [
                {
                    "apartment_id": "2026000001",
                    "apartment_name": "테스트 아파트",
                    "region_name": "서울",
                    "area_m2": 84,
                    "cutoff_score": 48,
                }
            ]
        )
        df.to_csv(MANUAL_CUTOFF_TEMPLATE_PATH, index=False)

        path = promote_manual_cutoff_template()
        promoted = pd.read_csv(path)

        assert str(promoted.loc[0, "apartment_id"]) == "2026000001"
        assert promoted.loc[0, "cutoff_score"] == 48
    finally:
        if original is not None:
            original.to_csv(MANUAL_CUTOFF_TEMPLATE_PATH, index=False)
        if original_manual is not None:
            original_manual.to_csv(MANUAL_CUTOFF_PATH, index=False)


def test_normalize_manual_cutoffs_rejects_missing_columns():
    df = pd.DataFrame([{"apartment_id": "sample-001"}])

    with pytest.raises(CutoffDataError):
        _normalize_manual_cutoffs(df, source=Path("bad.csv"))


def test_parse_public_api_rows_normalizes_odcloud_response():
    detail_rows = [
        {
            "HOUSE_MANAGE_NO": "2026000001",
            "PBLANC_NO": "2026000001",
            "HOUSE_NM": "테스트 아파트",
            "SUBSCRPT_AREA_CODE": "100",
            "SUBSCRPT_AREA_CODE_NM": "서울",
            "RCRIT_PBLANC_DE": "2026-04-01",
            "TOT_SUPLY_HSHLDCO": "120",
        }
    ]
    model_rows = [
        {
            "HOUSE_MANAGE_NO": "2026000001",
            "PBLANC_NO": "2026000001",
            "HOUSE_TY": "84",
            "SUPLY_HSHLDCO": "80",
            "LTTOT_TOP_AMOUNT": "750000000",
        }
    ]

    competition_rows = [
        {
            "HOUSE_MANAGE_NO": "2026000001",
            "PBLANC_NO": "2026000001",
            "CMPET_RATE": "12.5",
        }
    ]

    df = parse_public_api_rows(detail_rows, model_rows, competition_rows)

    assert df.loc[0, "apartment_id"] == "2026000001"
    assert df.loc[0, "apartment_name"] == "테스트 아파트"
    assert df.loc[0, "region_name"] == "서울"
    assert df.loc[0, "supply_year"] == 2026
    assert df.loc[0, "supply_quarter"] == 2
    assert df.loc[0, "general_supply_units"] == 80
    assert df.loc[0, "sale_price"] == 750000000
    assert df.loc[0, "area_m2"] == 84
    assert df.loc[0, "competition_rate"] == 12.5


def test_parse_competition_rows_normalizes_competition_response():
    rows = [
        {
            "HOUSE_MANAGE_NO": "2026000001",
            "PBLANC_NO": "2026000001",
            "HOUSE_TY": "84",
            "MODEL_NO": "01",
            "RESIDE_SENM": "해당지역",
            "SUBSCRPT_RANK_CODE": "1",
            "SUPLY_HSHLDCO": "10",
            "REQ_CNT": "125",
            "CMPET_RATE": "12.5",
        }
    ]

    df = parse_competition_rows(rows)

    assert df.loc[0, "house_manage_no"] == "2026000001"
    assert df.loc[0, "request_count"] == 125
    assert df.loc[0, "competition_rate"] == 12.5


def test_parse_special_supply_rows_sums_count_columns():
    rows = [
        {
            "HOUSE_MANAGE_NO": "2026000001",
            "PBLANC_NO": "2026000001",
            "HOUSE_TY": "84",
            "MODEL_NO": "01",
            "CRSPAREA_MNYCH_CNT": "3",
            "CTPRVN_MNYCH_CNT": "4",
        }
    ]

    df = parse_special_supply_rows(rows)

    assert df.loc[0, "house_manage_no"] == "2026000001"
    assert df.loc[0, "total_special_request_count"] == 7


def test_fetch_odcloud_rows_decodes_encoded_service_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"ok": True}]}

    def fake_get(url, params, timeout):
        captured["serviceKey"] = params["serviceKey"]
        return FakeResponse()

    monkeypatch.setattr("pipeline.collect_public_api.httpx.get", fake_get)

    rows = _fetch_odcloud_rows("endpoint", quote("abc+/=", safe=""))

    assert rows == [{"ok": True}]
    assert captured["serviceKey"] == "abc+/="


def test_preprocess_creates_clean_training_dataset():
    path = preprocess()
    df = pd.read_csv(path)

    assert path.exists()
    assert set(TRAINING_COLUMNS).issubset(df.columns)
    assert not df.empty


def test_build_features_creates_processed_training_dataset():
    path = build_features()
    df = pd.read_csv(path)

    assert path.exists()
    assert list(df.columns) == TRAINING_COLUMNS
    assert not df.empty
