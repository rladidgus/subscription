import pandas as pd
import pytest
from sqlalchemy import create_engine

from app.db.repository import (
    RepositoryDataError,
    _validate_columns,
    check_database_connection,
    list_processed_apartment_predictions,
    list_sample_apartment_predictions,
    load_processed_apartments,
    load_sample_apartments,
    load_training_dataset,
)


def test_load_sample_apartments_returns_dataframe():
    df = load_sample_apartments()

    assert not df.empty
    assert len(df) >= 20
    assert {"apartment_id", "apartment_name", "region_name", "predicted_cutoff_score"}.issubset(df.columns)


def test_load_processed_apartments_has_region_code():
    df = load_processed_apartments()

    assert "region_code" in df.columns


def test_load_training_dataset_has_expected_columns():
    df = load_training_dataset()

    assert {
        "apartment_id",
        "apartment_name",
        "region_code",
        "region_name",
        "cutoff_score",
    }.issubset(df.columns)


def test_list_sample_apartment_predictions_returns_schema_objects():
    apartments = list_sample_apartment_predictions()

    assert apartments
    assert apartments[0].apartment_id.startswith("apt-")


def test_list_processed_apartment_predictions_returns_schema_objects():
    apartments = list_processed_apartment_predictions()

    assert len(apartments) >= 20
    assert apartments[0].apartment_name


def test_validate_columns_raises_clear_error():
    df = pd.DataFrame([{"apartment_id": "apt-001"}])

    with pytest.raises(RepositoryDataError):
        _validate_columns(df, {"apartment_id", "apartment_name"}, source="test.csv")


def test_check_database_connection_with_sqlite_engine():
    engine = create_engine("sqlite:///:memory:")

    assert check_database_connection(engine) is True
