from pathlib import Path

import pandas as pd

from pipeline.collect_public_api import collect_public_api
from pipeline.collect_rone import collect_rone
from pipeline.collect_subscription_pdf import collect_subscription_pdf
from pipeline.common import (
    INTERIM_DIR,
    RAW_DIR,
    TRAINING_COLUMNS,
    ensure_data_dirs,
    normalize_apartment_name,
    read_sample_training_dataset,
    write_csv,
)


def preprocess() -> Path:
    ensure_data_dirs()
    public_path = RAW_DIR / "public_api" / "public_apartment_supply.csv"
    cutoff_path = RAW_DIR / "subscription_home" / "subscription_cutoffs.csv"
    rone_path = RAW_DIR / "rone" / "housing_price_index.csv"

    if not public_path.exists():
        collect_public_api()
    if not cutoff_path.exists():
        collect_subscription_pdf()
    if not rone_path.exists():
        collect_rone()

    public_df = pd.read_csv(public_path)
    cutoff_df = pd.read_csv(cutoff_path)
    rone_df = pd.read_csv(rone_path)

    for df in [public_df, cutoff_df]:
        df["apartment_id"] = df["apartment_id"].astype(str).str.strip()
        df["apartment_name"] = df["apartment_name"].map(normalize_apartment_name)
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")

    merged = public_df.merge(
        cutoff_df[["apartment_id", "area_m2", "cutoff_score"]],
        on=["apartment_id", "area_m2"],
        how="inner",
    )
    merged = merged.merge(
        rone_df[["region_code", "housing_price_index"]],
        on="region_code",
        how="left",
    )
    fallback_housing_price_index = merged["housing_price_index"].median()
    if pd.isna(fallback_housing_price_index):
        fallback_housing_price_index = 100.0
    merged["housing_price_index"] = merged["housing_price_index"].fillna(
        fallback_housing_price_index
    )
    merged = merged.dropna(subset=["cutoff_score", "region_code", "general_supply_units"])
    if merged.empty:
        merged = read_sample_training_dataset()

    merged = merged[TRAINING_COLUMNS]

    output_path = INTERIM_DIR / "clean_training_dataset.csv"
    return write_csv(merged, output_path)


if __name__ == "__main__":
    print(preprocess())
