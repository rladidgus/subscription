from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"

TRAINING_COLUMNS = [
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
]


def ensure_data_dirs() -> None:
    for path in [
        RAW_DIR / "subscription_home",
        RAW_DIR / "public_api",
        RAW_DIR / "rone",
        INTERIM_DIR,
        PROCESSED_DIR,
        SAMPLE_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def read_sample_training_dataset() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_DIR / "sample_training_dataset.csv")


def normalize_apartment_name(value: str) -> str:
    return " ".join(str(value).replace("\u3000", " ").split())
