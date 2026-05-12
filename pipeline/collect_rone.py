from pathlib import Path

from pipeline.common import RAW_DIR, ensure_data_dirs, read_sample_training_dataset, write_csv


def collect_rone() -> Path:
    ensure_data_dirs()
    sample = read_sample_training_dataset()
    df = sample[["region_code", "region_name", "housing_price_index"]].drop_duplicates()
    output_path = RAW_DIR / "rone" / "housing_price_index.csv"
    return write_csv(df, output_path)


if __name__ == "__main__":
    print(collect_rone())
