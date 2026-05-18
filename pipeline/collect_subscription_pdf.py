from pathlib import Path

import pandas as pd

from pipeline.common import RAW_DIR, ensure_data_dirs, read_sample_training_dataset, write_csv
from pipeline.import_applyhome_csv import has_applyhome_cutoff_files, import_applyhome_cutoffs

MANUAL_CUTOFF_PATH = RAW_DIR / "subscription_home" / "manual_subscription_cutoffs.csv"
MANUAL_CUTOFF_TEMPLATE_PATH = RAW_DIR / "subscription_home" / "manual_subscription_cutoffs_template.csv"
STANDARD_CUTOFF_PATH = RAW_DIR / "subscription_home" / "subscription_cutoffs.csv"
PUBLIC_SUPPLY_PATH = RAW_DIR / "public_api" / "public_apartment_supply.csv"
REQUIRED_CUTOFF_COLUMNS = {
    "apartment_id",
    "apartment_name",
    "region_name",
    "area_m2",
    "cutoff_score",
}


class CutoffDataError(ValueError):
    pass


def _validate_cutoff_columns(df: pd.DataFrame, source: Path) -> None:
    missing = sorted(REQUIRED_CUTOFF_COLUMNS - set(df.columns))
    if missing:
        raise CutoffDataError(f"{source} 필수 컬럼이 누락되었습니다: {', '.join(missing)}")


def _normalize_manual_cutoffs(df: pd.DataFrame, source: Path) -> pd.DataFrame:
    _validate_cutoff_columns(df, source)
    normalized = df[list(REQUIRED_CUTOFF_COLUMNS)].copy()
    normalized["apartment_id"] = normalized["apartment_id"].astype(str).str.strip()
    normalized["apartment_name"] = normalized["apartment_name"].astype(str).str.strip()
    normalized["region_name"] = normalized["region_name"].astype(str).str.strip()
    normalized["area_m2"] = pd.to_numeric(normalized["area_m2"], errors="coerce")
    normalized["cutoff_score"] = pd.to_numeric(normalized["cutoff_score"], errors="coerce")
    normalized = normalized.dropna(subset=["apartment_id", "apartment_name", "area_m2", "cutoff_score"])
    normalized = normalized[(normalized["cutoff_score"] >= 0) & (normalized["cutoff_score"] <= 84)]
    return normalized[
        ["apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"]
    ]


def _has_filled_cutoff_scores(path: Path) -> bool:
    if not path.exists():
        return False
    df = pd.read_csv(path)
    if "cutoff_score" not in df.columns:
        return False
    return pd.to_numeric(df["cutoff_score"], errors="coerce").notna().any()


def create_manual_cutoff_template(overwrite: bool = False) -> Path:
    ensure_data_dirs()
    if MANUAL_CUTOFF_PATH.exists() and not overwrite:
        return MANUAL_CUTOFF_PATH

    sample = read_sample_training_dataset()
    columns = ["apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"]
    return write_csv(sample[columns], MANUAL_CUTOFF_PATH)


def create_manual_cutoff_template_from_public_supply(overwrite: bool = False) -> Path:
    ensure_data_dirs()
    if MANUAL_CUTOFF_TEMPLATE_PATH.exists() and not overwrite:
        return MANUAL_CUTOFF_TEMPLATE_PATH

    if PUBLIC_SUPPLY_PATH.exists():
        source = pd.read_csv(PUBLIC_SUPPLY_PATH)
    else:
        source = read_sample_training_dataset()

    columns = ["apartment_id", "apartment_name", "region_name", "area_m2"]
    template = source[columns].drop_duplicates().copy()
    template["cutoff_score"] = ""
    template = template[["apartment_id", "apartment_name", "region_name", "area_m2", "cutoff_score"]]
    return write_csv(template, MANUAL_CUTOFF_TEMPLATE_PATH)


def promote_manual_cutoff_template() -> Path:
    ensure_data_dirs()
    if not MANUAL_CUTOFF_TEMPLATE_PATH.exists():
        create_manual_cutoff_template_from_public_supply()

    template_df = pd.read_csv(MANUAL_CUTOFF_TEMPLATE_PATH)
    normalized = _normalize_manual_cutoffs(template_df, MANUAL_CUTOFF_TEMPLATE_PATH)
    if normalized.empty:
        raise CutoffDataError(
            f"{MANUAL_CUTOFF_TEMPLATE_PATH}에 입력된 cutoff_score가 없습니다."
        )
    return write_csv(normalized, MANUAL_CUTOFF_PATH)


def collect_subscription_pdf() -> Path:
    ensure_data_dirs()
    if has_applyhome_cutoff_files():
        return import_applyhome_cutoffs()
    if _has_filled_cutoff_scores(MANUAL_CUTOFF_TEMPLATE_PATH):
        promote_manual_cutoff_template()
    elif not MANUAL_CUTOFF_PATH.exists():
        create_manual_cutoff_template()

    manual_df = pd.read_csv(MANUAL_CUTOFF_PATH)
    normalized = _normalize_manual_cutoffs(manual_df, MANUAL_CUTOFF_PATH)
    return write_csv(normalized, STANDARD_CUTOFF_PATH)


if __name__ == "__main__":
    print(collect_subscription_pdf())
