from pathlib import Path

import pandas as pd

from pipeline.common import INTERIM_DIR, PROCESSED_DIR, TRAINING_COLUMNS, write_csv
from pipeline.preprocess import preprocess


def build_features() -> Path:
    interim_path = INTERIM_DIR / "clean_training_dataset.csv"
    if not interim_path.exists():
        preprocess()

    df = pd.read_csv(interim_path)
    df["announcement_date"] = pd.to_datetime(df["announcement_date"])
    df["supply_year"] = df["announcement_date"].dt.year
    df["supply_quarter"] = df["announcement_date"].dt.quarter
    df["region_code"] = df["region_code"].astype(str).str.zfill(2)
    df = df[TRAINING_COLUMNS]

    output_path = PROCESSED_DIR / "training_dataset.csv"
    return write_csv(df, output_path)


if __name__ == "__main__":
    print(build_features())
