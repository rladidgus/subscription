from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.schemas.apartment import ApartmentPrediction
from app.schemas.prediction import CutoffPredictionRequest


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SAMPLE_APARTMENTS_PATH = DATA_DIR / "sample" / "sample_apartment_candidates.csv"
PROCESSED_APARTMENTS_PATH = DATA_DIR / "processed" / "apartment_candidates.csv"
TRAINING_DATASET_PATH = DATA_DIR / "processed" / "training_dataset.csv"

APARTMENT_CANDIDATE_COLUMNS = {
    "apartment_id",
    "apartment_name",
    "region_name",
    "predicted_cutoff_score",
}
PROCESSED_APARTMENT_COLUMNS = APARTMENT_CANDIDATE_COLUMNS | {"region_code"}
TRAINING_DATASET_COLUMNS = {
    "apartment_id",
    "apartment_name",
    "region_code",
    "region_name",
    "announcement_date",
    "supply_year",
    "supply_quarter",
    "general_supply_units",
    "sale_price",
    "competition_rate",
    "housing_price_index",
    "area_m2",
    "cutoff_score",
}


class RepositoryDataError(ValueError):
    pass


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
    return pd.read_csv(path)


def _validate_columns(df: pd.DataFrame, required_columns: set[str], source: Path) -> None:
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise RepositoryDataError(f"{source} 필수 컬럼이 누락되었습니다: {', '.join(missing)}")


def load_sample_apartments() -> pd.DataFrame:
    df = _read_csv(SAMPLE_APARTMENTS_PATH)
    _validate_columns(df, APARTMENT_CANDIDATE_COLUMNS, SAMPLE_APARTMENTS_PATH)
    return df


def load_processed_apartments() -> pd.DataFrame:
    df = _read_csv(PROCESSED_APARTMENTS_PATH)
    _validate_columns(df, PROCESSED_APARTMENT_COLUMNS, PROCESSED_APARTMENTS_PATH)
    return df


def load_training_dataset() -> pd.DataFrame:
    df = _read_csv(TRAINING_DATASET_PATH)
    _validate_columns(df, TRAINING_DATASET_COLUMNS, TRAINING_DATASET_PATH)
    return df


def list_sample_apartment_predictions() -> list[ApartmentPrediction]:
    df = load_sample_apartments()
    return [ApartmentPrediction(**row) for row in df.to_dict(orient="records")]


def list_processed_apartment_predictions() -> list[ApartmentPrediction]:
    df = load_processed_apartments()
    return [ApartmentPrediction(**row) for row in df.to_dict(orient="records")]


def list_processed_cutoff_requests() -> list[CutoffPredictionRequest]:
    df = load_training_dataset()
    if df.empty:
        return []
    return [
        CutoffPredictionRequest(
            apartment_name=row["apartment_name"],
            region_code=str(row["region_code"]),
            general_supply_units=int(row["general_supply_units"]),
            sale_price=float(row["sale_price"]),
            competition_rate=float(row["competition_rate"]),
            housing_price_index=float(row["housing_price_index"]),
            supply_year=int(row["supply_year"]),
            supply_quarter=int(row["supply_quarter"]),
            area_m2=float(row["area_m2"]),
        )
        for row in df.to_dict(orient="records")
    ]


def check_database_connection(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
