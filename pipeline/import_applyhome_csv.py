from pathlib import Path
import os

import pandas as pd

from pipeline.common import RAW_DIR, ensure_data_dirs, write_csv


APPLYHOME_RAW_DIR = RAW_DIR / "applyhome"
DEFAULT_APPLYHOME_SOURCE_DIR = Path.home() / "Downloads"

DETAIL_FILENAME = "apt_lttot_pblanc_detail.csv"
MODEL_FILENAME = "apt_lttot_pblanc_model.csv"
COMPETITION_FILENAME = "apt_lttot_pblanc_competition.csv"
SCORE_FILENAME = "apt_lttot_pblanc_score.csv"
MART_FILENAME = "applyhome_apartment_mart.csv"

PUBLIC_SUPPLY_OUTPUT_PATH = RAW_DIR / "public_api" / "public_apartment_supply.csv"
COMPETITION_OUTPUT_PATH = RAW_DIR / "public_api" / "apt_competition.csv"
CUTOFF_OUTPUT_PATH = RAW_DIR / "subscription_home" / "subscription_cutoffs.csv"

REGION_CODE_BY_NAME = {
    "서울": "11",
    "부산": "26",
    "대구": "27",
    "인천": "28",
    "광주": "29",
    "대전": "30",
    "울산": "31",
    "세종": "36",
    "경기": "41",
    "강원": "51",
    "충북": "43",
    "충남": "44",
    "전북": "52",
    "전남": "46",
    "경북": "47",
    "경남": "48",
    "제주": "50",
}


def _source_dir(source_dir: Path | str | None = None) -> Path:
    if source_dir is not None:
        return Path(source_dir)
    configured = os.getenv("APPLYHOME_CSV_DIR")
    if configured:
        return Path(configured)
    if APPLYHOME_RAW_DIR.exists():
        return APPLYHOME_RAW_DIR
    return DEFAULT_APPLYHOME_SOURCE_DIR


def _path(filename: str, source_dir: Path | str | None = None) -> Path:
    return _source_dir(source_dir) / filename


def has_applyhome_public_supply_files(source_dir: Path | str | None = None) -> bool:
    if _path(MART_FILENAME, source_dir).exists():
        return True
    return all(
        _path(filename, source_dir).exists()
        for filename in [DETAIL_FILENAME, MODEL_FILENAME, COMPETITION_FILENAME]
    )


def has_applyhome_cutoff_files(source_dir: Path | str | None = None) -> bool:
    return all(
        _path(filename, source_dir).exists()
        for filename in [DETAIL_FILENAME, SCORE_FILENAME]
    )


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949")


def _to_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.extract(r"(\d+(?:\.\d+)?)")[0],
        errors="coerce",
    )


def _normalize_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for column in ["HOUSE_MANAGE_NO", "PBLANC_NO", "MODEL_NO", "HOUSE_TY"]:
        if column in normalized.columns:
            normalized[column] = normalized[column].astype(str).str.strip()
    return normalized


def _prepare_detail(detail_df: pd.DataFrame) -> pd.DataFrame:
    detail = _normalize_key_columns(detail_df)
    detail["announcement_date"] = pd.to_datetime(detail["RCRIT_PBLANC_DE"], errors="coerce")
    return detail[
        [
            "HOUSE_MANAGE_NO",
            "PBLANC_NO",
            "HOUSE_NM",
            "SUBSCRPT_AREA_CODE",
            "SUBSCRPT_AREA_CODE_NM",
            "RCRIT_PBLANC_DE",
            "announcement_date",
            "TOT_SUPLY_HSHLDCO",
        ]
    ].copy()


def _standard_region_code(region_name: object, fallback_code: object) -> str:
    normalized_name = str(region_name or "").strip()
    if normalized_name in REGION_CODE_BY_NAME:
        return REGION_CODE_BY_NAME[normalized_name]
    return str(fallback_code or "").strip()


def _competition_summary(competition_df: pd.DataFrame) -> pd.DataFrame:
    competition = _normalize_key_columns(competition_df)
    competition["competition_rate"] = _to_numeric_series(competition["CMPET_RATE"]).fillna(0)
    competition["request_count"] = _to_numeric_series(competition["REQ_CNT"]).fillna(0)
    return (
        competition.groupby(
            ["HOUSE_MANAGE_NO", "PBLANC_NO", "MODEL_NO", "HOUSE_TY"],
            as_index=False,
        )
        .agg(
            competition_rate=("competition_rate", "max"),
            request_count=("request_count", "sum"),
        )
    )


def _public_supply_from_model_rows(model_rows: pd.DataFrame) -> pd.DataFrame:
    region_code_source = (
        model_rows["SUBSCRPT_AREA_CODE"]
        if "SUBSCRPT_AREA_CODE" in model_rows.columns
        else pd.Series([""] * len(model_rows), index=model_rows.index)
    )
    return pd.DataFrame(
        {
            "apartment_id": model_rows["HOUSE_MANAGE_NO"],
            "apartment_name": model_rows["HOUSE_NM"].fillna(""),
            "region_code": [
                _standard_region_code(region_name, region_code)
                for region_name, region_code in zip(
                    model_rows["SUBSCRPT_AREA_CODE_NM"],
                    region_code_source,
                    strict=False,
                )
            ],
            "region_name": model_rows["SUBSCRPT_AREA_CODE_NM"].fillna(""),
            "announcement_date": model_rows["announcement_date"].dt.strftime("%Y-%m-%d").fillna(""),
            "supply_year": model_rows["announcement_date"].dt.year.fillna(0).astype(int),
            "supply_quarter": model_rows["announcement_date"].dt.quarter.fillna(0).astype(int),
            "general_supply_units": _to_numeric_series(model_rows["SUPLY_HSHLDCO"]).fillna(0).astype(int),
            "sale_price": _to_numeric_series(model_rows["LTTOT_TOP_AMOUNT"]).fillna(0),
            "competition_rate": model_rows["competition_rate"].fillna(0),
            "area_m2": _to_numeric_series(model_rows["HOUSE_TY"]),
        }
    ).dropna(subset=["area_m2"]).drop_duplicates()


def _import_applyhome_public_supply_from_mart(source_dir: Path | str | None = None) -> Path:
    mart = _normalize_key_columns(_read_csv(_path(MART_FILENAME, source_dir)))
    mart["announcement_date"] = pd.to_datetime(mart["RCRIT_PBLANC_DE"], errors="coerce")
    mart["competition_rate"] = _to_numeric_series(mart["max_competition_rate"]).fillna(0)
    output = _public_supply_from_model_rows(mart)

    competition_output = pd.DataFrame(
        {
            "house_manage_no": mart["HOUSE_MANAGE_NO"],
            "pblanc_no": mart["PBLANC_NO"],
            "house_type": mart["HOUSE_TY"],
            "model_no": mart["MODEL_NO"],
            "reside_name": "",
            "subscription_rank": "",
            "supply_units": _to_numeric_series(mart["SUPLY_HSHLDCO"]).fillna(0).astype(int),
            "request_count": _to_numeric_series(mart["total_req_cnt"]).fillna(0).astype(int),
            "competition_rate": mart["competition_rate"],
        }
    ).drop_duplicates()
    write_csv(competition_output, COMPETITION_OUTPUT_PATH)
    return write_csv(output, PUBLIC_SUPPLY_OUTPUT_PATH)


def import_applyhome_public_supply(source_dir: Path | str | None = None) -> Path:
    ensure_data_dirs()
    if not has_applyhome_public_supply_files(source_dir):
        raise FileNotFoundError(f"ApplyHome APT 원천 CSV를 찾을 수 없습니다: {_source_dir(source_dir)}")
    if _path(MART_FILENAME, source_dir).exists():
        return _import_applyhome_public_supply_from_mart(source_dir)

    detail = _prepare_detail(_read_csv(_path(DETAIL_FILENAME, source_dir)))
    model = _normalize_key_columns(_read_csv(_path(MODEL_FILENAME, source_dir)))
    competition = _competition_summary(_read_csv(_path(COMPETITION_FILENAME, source_dir)))

    merged = model.merge(detail, on=["HOUSE_MANAGE_NO", "PBLANC_NO"], how="left")
    merged = merged.merge(
        competition,
        on=["HOUSE_MANAGE_NO", "PBLANC_NO", "MODEL_NO", "HOUSE_TY"],
        how="left",
    )

    output = _public_supply_from_model_rows(merged)

    competition_output = competition.rename(
        columns={
            "HOUSE_MANAGE_NO": "house_manage_no",
            "PBLANC_NO": "pblanc_no",
            "HOUSE_TY": "house_type",
            "MODEL_NO": "model_no",
        }
    )
    competition_output["reside_name"] = ""
    competition_output["subscription_rank"] = ""
    competition_output["supply_units"] = 0
    competition_output = competition_output[
        [
            "house_manage_no",
            "pblanc_no",
            "house_type",
            "model_no",
            "reside_name",
            "subscription_rank",
            "supply_units",
            "request_count",
            "competition_rate",
        ]
    ]
    write_csv(competition_output, COMPETITION_OUTPUT_PATH)
    return write_csv(output, PUBLIC_SUPPLY_OUTPUT_PATH)


def import_applyhome_cutoffs(source_dir: Path | str | None = None) -> Path:
    ensure_data_dirs()
    if not has_applyhome_cutoff_files(source_dir):
        raise FileNotFoundError(f"ApplyHome 당첨가점 CSV를 찾을 수 없습니다: {_source_dir(source_dir)}")

    detail = _prepare_detail(_read_csv(_path(DETAIL_FILENAME, source_dir)))
    score = _normalize_key_columns(_read_csv(_path(SCORE_FILENAME, source_dir)))
    merged = score.merge(detail, on=["HOUSE_MANAGE_NO", "PBLANC_NO"], how="left")

    output = pd.DataFrame(
        {
            "apartment_id": merged["HOUSE_MANAGE_NO"],
            "apartment_name": merged["HOUSE_NM"].fillna(""),
            "region_name": merged["SUBSCRPT_AREA_CODE_NM"].fillna(""),
            "area_m2": _to_numeric_series(merged["HOUSE_TY"]),
            "cutoff_score": _to_numeric_series(merged["LWET_SCORE"]),
        }
    )
    output = output.dropna(subset=["apartment_id", "apartment_name", "area_m2", "cutoff_score"])
    output = output[(output["cutoff_score"] >= 0) & (output["cutoff_score"] <= 84)]
    output = (
        output.groupby(["apartment_id", "apartment_name", "region_name", "area_m2"], as_index=False)
        .agg(cutoff_score=("cutoff_score", "min"))
        .sort_values(["apartment_id", "area_m2"])
    )
    return write_csv(output, CUTOFF_OUTPUT_PATH)


def import_applyhome_csvs(source_dir: Path | str | None = None) -> list[Path]:
    return [
        import_applyhome_public_supply(source_dir),
        import_applyhome_cutoffs(source_dir),
    ]


if __name__ == "__main__":
    for output_path in import_applyhome_csvs():
        print(output_path)
