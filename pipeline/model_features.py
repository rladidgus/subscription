from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.schemas.prediction import CutoffPredictionRequest
from pipeline.common import PROCESSED_DIR, RAW_DIR, write_csv
from pipeline.import_applyhome_csv import (
    COMPETITION_FILENAME,
    DETAIL_FILENAME,
    MART_FILENAME,
    MODEL_FILENAME,
    SCORE_FILENAME,
    REGION_CODE_BY_NAME,
    _normalize_key_columns,
    _read_csv,
    _source_dir,
    _to_numeric_series,
)


MODEL_FEATURE_COLUMNS = [
    "log_cmpet_rate",
    "SUPLY_HSHLDCO",
    "spsply_ratio",
    "SUBSCRPT_RANK_CODE",
    "RESIDE_SECD",
    "SPECLT_RDN_EARTH_AT",
    "MDAT_TRGET_AREA_SECD",
    "PARCPRC_ULS_AT",
    "IMPRMN_BSNS_AT",
    "PUBLIC_HOUSE_EARTH_AT",
    "LRSCL_BLDLND_AT",
    "NPLN_PRVOPR_PUBLIC_HOUSE_AT",
    "log_lttot_top_amount",
    "house_area",
    "is_top_brand",
    "price_rank_in_region",
    "cmpet_rank_in_region",
    "region_score_lag1",
    "region_score_roll5_mean",
    "region_score_roll5_std",
    "notice_year",
    "notice_month",
]

MODEL_TARGET_COLUMN = "LWET_SCORE"
MODEL_FEATURE_DATASET_PATH = PROCESSED_DIR / "applyhome_model_features.csv"

TOP_BRANDS = ["래미안", "힐스테이트", "푸르지오", "아이파크", "자이", "e편한세상", "더샵", "롯데캐슬"]
FLAG_COLUMNS = [
    "SPECLT_RDN_EARTH_AT",
    "PARCPRC_ULS_AT",
    "IMPRMN_BSNS_AT",
    "PUBLIC_HOUSE_EARTH_AT",
    "LRSCL_BLDLND_AT",
    "NPLN_PRVOPR_PUBLIC_HOUSE_AT",
]


def _path(filename: str, source_dir: Path | str | None = None) -> Path:
    return _source_dir(source_dir) / filename


def _normalize_model_no(df: pd.DataFrame) -> pd.DataFrame:
    normalized = _normalize_key_columns(df)
    if "MODEL_NO" in normalized.columns:
        normalized["MODEL_NO"] = normalized["MODEL_NO"].astype(str).str.strip().str.zfill(2)
    return normalized


def _normalize_lookup_value(value: str | int | float | None, width: int | None = None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    if width is not None:
        normalized = normalized.zfill(width)
    return normalized


def _yes_no_to_int(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.upper()
        .map({"Y": 1, "N": 0, "1": 1, "0": 0, "TRUE": 1, "FALSE": 0})
        .fillna(0)
        .astype(int)
    )


def _binary_code_to_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.strip().replace({"Y": "1", "N": "0"}), errors="coerce").fillna(0)


def _safe_log1p(series: pd.Series) -> pd.Series:
    return np.log1p(pd.to_numeric(series, errors="coerce").clip(lower=0).fillna(0))


def _safe_log10_1p(series: pd.Series) -> pd.Series:
    return np.log10(pd.to_numeric(series, errors="coerce").clip(lower=0).fillna(0) + 1)


def _clean_competition_rate(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.extract(r"(-?\d+(?:\.\d+)?)")[0],
        errors="coerce",
    )
    return numeric.clip(lower=0).fillna(0)


def _region_code(region_name: object, fallback_code: object = "") -> str:
    name = str(region_name or "").strip()
    if name in REGION_CODE_BY_NAME:
        return REGION_CODE_BY_NAME[name]
    return str(fallback_code or "").strip()


def _load_applyhome_sources(source_dir: Path | str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    detail = _normalize_model_no(_read_csv(_path(DETAIL_FILENAME, source_dir)))
    model = _normalize_model_no(_read_csv(_path(MODEL_FILENAME, source_dir)))
    competition = _normalize_model_no(_read_csv(_path(COMPETITION_FILENAME, source_dir)))
    score = _normalize_model_no(_read_csv(_path(SCORE_FILENAME, source_dir)))
    mart_path = _path(MART_FILENAME, source_dir)
    mart = _normalize_model_no(_read_csv(mart_path)) if mart_path.exists() else None
    return detail, model, competition, score, mart


def build_applyhome_model_features(source_dir: Path | str | None = None) -> Path:
    detail, model, competition, score, mart = _load_applyhome_sources(source_dir)
    detail["announcement_date"] = pd.to_datetime(detail["RCRIT_PBLANC_DE"], errors="coerce")
    score[MODEL_TARGET_COLUMN] = _to_numeric_series(score["LWET_SCORE"])

    keys = ["HOUSE_MANAGE_NO", "PBLANC_NO", "MODEL_NO", "HOUSE_TY"]
    merged = competition.merge(model, on=keys, how="left", suffixes=("_COMP", ""))
    detail_columns = [
        "HOUSE_MANAGE_NO",
        "PBLANC_NO",
        "HOUSE_NM",
        "SUBSCRPT_AREA_CODE",
        "SUBSCRPT_AREA_CODE_NM",
        "RCRIT_PBLANC_DE",
        "announcement_date",
        "MDAT_TRGET_AREA_SECD",
        "SPECLT_RDN_EARTH_AT",
        "PARCPRC_ULS_AT",
        "IMPRMN_BSNS_AT",
        "PUBLIC_HOUSE_EARTH_AT",
        "LRSCL_BLDLND_AT",
        "NPLN_PRVOPR_PUBLIC_HOUSE_AT",
        "TOT_SUPLY_HSHLDCO",
    ]
    merged = merged.merge(detail[detail_columns], on=["HOUSE_MANAGE_NO", "PBLANC_NO"], how="left")
    merged = merged.merge(score[keys + ["RESIDE_SECD", MODEL_TARGET_COLUMN]], on=keys + ["RESIDE_SECD"], how="left")

    if mart is not None and "special_supply_ratio" in mart.columns:
        merged = merged.merge(
            mart[keys + ["special_supply_ratio"]].drop_duplicates(keys),
            on=keys,
            how="left",
        )
    else:
        merged["special_supply_ratio"] = np.nan

    for column in FLAG_COLUMNS:
        if column not in merged.columns:
            merged[column] = 0
        merged[column] = _yes_no_to_int(merged[column])

    merged["MDAT_TRGET_AREA_SECD"] = _binary_code_to_int(merged["MDAT_TRGET_AREA_SECD"])
    merged["CMPET_RATE_NUM"] = _clean_competition_rate(merged["CMPET_RATE"])
    merged["LTTOT_TOP_AMOUNT_NUM"] = _to_numeric_series(merged["LTTOT_TOP_AMOUNT"])
    merged["HOUSE_AREA_NUM"] = _to_numeric_series(merged["HOUSE_TY"])
    merged["SUPLY_HSHLDCO_NUM"] = _to_numeric_series(merged["SUPLY_HSHLDCO"]).fillna(0)
    merged["SPSPLY_HSHLDCO_NUM"] = _to_numeric_series(merged["SPSPLY_HSHLDCO"]).fillna(0)
    total_supply = merged["SPSPLY_HSHLDCO_NUM"] + merged["SUPLY_HSHLDCO_NUM"]
    computed_spsply_ratio = (merged["SPSPLY_HSHLDCO_NUM"] / total_supply.replace(0, np.nan)).fillna(0)
    merged["spsply_ratio"] = pd.to_numeric(merged["special_supply_ratio"], errors="coerce").fillna(computed_spsply_ratio)
    merged["region_code"] = [
        _region_code(region_name, region_code)
        for region_name, region_code in zip(
            merged["SUBSCRPT_AREA_CODE_NM"],
            merged["SUBSCRPT_AREA_CODE"],
            strict=False,
        )
    ]
    merged["notice_year"] = merged["announcement_date"].dt.year
    merged["notice_month"] = merged["announcement_date"].dt.month
    merged["is_top_brand"] = merged["HOUSE_NM"].fillna("").apply(lambda name: int(any(brand in str(name) for brand in TOP_BRANDS)))

    merged["price_rank_in_region"] = merged.groupby("region_code")["LTTOT_TOP_AMOUNT_NUM"].rank(pct=True).fillna(0)
    merged["cmpet_rank_in_region"] = merged.groupby("region_code")["CMPET_RATE_NUM"].rank(pct=True).fillna(0)

    merged = merged.sort_values(["region_code", "announcement_date", "HOUSE_MANAGE_NO", "MODEL_NO", "RESIDE_SECD"])
    shifted_score = merged.groupby("region_code")[MODEL_TARGET_COLUMN].shift(1)
    merged["region_score_lag1"] = shifted_score
    merged["region_score_roll5_mean"] = (
        shifted_score.groupby(merged["region_code"]).rolling(5, min_periods=1).mean().reset_index(level=0, drop=True)
    )
    merged["region_score_roll5_std"] = (
        shifted_score.groupby(merged["region_code"]).rolling(5, min_periods=2).std().reset_index(level=0, drop=True)
    )

    global_score_median = merged[MODEL_TARGET_COLUMN].median()
    for column in ["region_score_lag1", "region_score_roll5_mean"]:
        merged[column] = merged[column].fillna(global_score_median if pd.notna(global_score_median) else 0)
    merged["region_score_roll5_std"] = merged["region_score_roll5_std"].fillna(0)

    output = pd.DataFrame(
        {
            "HOUSE_MANAGE_NO": merged["HOUSE_MANAGE_NO"],
            "PBLANC_NO": merged["PBLANC_NO"],
            "MODEL_NO": merged["MODEL_NO"],
            "HOUSE_TY": merged["HOUSE_TY"],
            "HOUSE_NM": merged["HOUSE_NM"],
            "region_code": merged["region_code"],
            "announcement_date": merged["announcement_date"].dt.strftime("%Y-%m-%d"),
            MODEL_TARGET_COLUMN: merged[MODEL_TARGET_COLUMN],
            "log_cmpet_rate": _safe_log1p(merged["CMPET_RATE_NUM"]),
            "SUPLY_HSHLDCO": merged["SUPLY_HSHLDCO_NUM"],
            "spsply_ratio": merged["spsply_ratio"],
            "SUBSCRPT_RANK_CODE": pd.to_numeric(merged["SUBSCRPT_RANK_CODE"], errors="coerce").fillna(-1),
            "RESIDE_SECD": pd.to_numeric(merged["RESIDE_SECD"], errors="coerce").fillna(-1),
            "SPECLT_RDN_EARTH_AT": merged["SPECLT_RDN_EARTH_AT"],
            "MDAT_TRGET_AREA_SECD": merged["MDAT_TRGET_AREA_SECD"],
            "PARCPRC_ULS_AT": merged["PARCPRC_ULS_AT"],
            "IMPRMN_BSNS_AT": merged["IMPRMN_BSNS_AT"],
            "PUBLIC_HOUSE_EARTH_AT": merged["PUBLIC_HOUSE_EARTH_AT"],
            "LRSCL_BLDLND_AT": merged["LRSCL_BLDLND_AT"],
            "NPLN_PRVOPR_PUBLIC_HOUSE_AT": merged["NPLN_PRVOPR_PUBLIC_HOUSE_AT"],
            "log_lttot_top_amount": _safe_log10_1p(merged["LTTOT_TOP_AMOUNT_NUM"]),
            "house_area": merged["HOUSE_AREA_NUM"],
            "is_top_brand": merged["is_top_brand"],
            "price_rank_in_region": merged["price_rank_in_region"],
            "cmpet_rank_in_region": merged["cmpet_rank_in_region"],
            "region_score_lag1": merged["region_score_lag1"],
            "region_score_roll5_mean": merged["region_score_roll5_mean"],
            "region_score_roll5_std": merged["region_score_roll5_std"],
            "notice_year": merged["notice_year"],
            "notice_month": merged["notice_month"],
        }
    )
    output = output.dropna(subset=["house_area", "notice_year", "notice_month"])
    output[MODEL_FEATURE_COLUMNS] = output[MODEL_FEATURE_COLUMNS].fillna(0)
    return write_csv(output, MODEL_FEATURE_DATASET_PATH)


def load_or_build_model_feature_dataset() -> pd.DataFrame:
    if not MODEL_FEATURE_DATASET_PATH.exists():
        source_dir = RAW_DIR / "applyhome"
        build_applyhome_model_features(source_dir if source_dir.exists() else None)
    df = pd.read_csv(MODEL_FEATURE_DATASET_PATH)
    for column in ["HOUSE_MANAGE_NO", "PBLANC_NO", "HOUSE_TY", "region_code"]:
        if column in df.columns:
            df[column] = df[column].astype(str).str.strip()
    for column in ["MODEL_NO", "RESIDE_SECD"]:
        if column in df.columns:
            df[column] = df[column].astype(str).str.strip().str.zfill(2)
    if "SUBSCRPT_RANK_CODE" in df.columns:
        df["SUBSCRPT_RANK_CODE"] = df["SUBSCRPT_RANK_CODE"].astype(str).str.strip()
    return df


def find_applyhome_feature_rows(
    apartment_name: str | None = None,
    region_code: str | None = None,
    house_manage_no: str | None = None,
    pblanc_no: str | None = None,
    model_no: str | None = None,
    house_type: str | None = None,
    reside_secd: str | None = None,
    subscription_rank_code: str | None = None,
    limit: int = 20,
) -> pd.DataFrame:
    df = load_or_build_model_feature_dataset()
    filtered = df

    if apartment_name:
        filtered = filtered[filtered["HOUSE_NM"].fillna("").str.contains(apartment_name, case=False, regex=False)]
    if region_code:
        filtered = filtered[filtered["region_code"].astype(str).str.strip() == str(region_code).strip()]

    lookup_pairs = [
        ("HOUSE_MANAGE_NO", _normalize_lookup_value(house_manage_no)),
        ("PBLANC_NO", _normalize_lookup_value(pblanc_no)),
        ("MODEL_NO", _normalize_lookup_value(model_no, width=2)),
        ("HOUSE_TY", _normalize_lookup_value(house_type)),
        ("RESIDE_SECD", _normalize_lookup_value(reside_secd, width=2)),
        ("SUBSCRPT_RANK_CODE", _normalize_lookup_value(subscription_rank_code)),
    ]
    for column, value in lookup_pairs:
        if value is not None:
            filtered = filtered[filtered[column].astype(str).str.strip() == value]

    sort_columns = [column for column in ["announcement_date", "HOUSE_MANAGE_NO", "MODEL_NO", "HOUSE_TY"] if column in filtered.columns]
    if sort_columns:
        filtered = filtered.sort_values(sort_columns, ascending=[False] + [True] * (len(sort_columns) - 1))
    return filtered.head(limit).reset_index(drop=True)


def features_from_applyhome_row(row: pd.Series) -> pd.DataFrame:
    features = pd.DataFrame([{column: row[column] for column in MODEL_FEATURE_COLUMNS}], columns=MODEL_FEATURE_COLUMNS)
    return features.apply(pd.to_numeric, errors="coerce").fillna(0)


@lru_cache(maxsize=1)
def _feature_stats() -> dict[str, object]:
    try:
        df = load_or_build_model_feature_dataset()
    except (FileNotFoundError, KeyError):
        return {}

    valid_scores = pd.to_numeric(df.get(MODEL_TARGET_COLUMN), errors="coerce")
    stats: dict[str, object] = {
        "global_score": float(valid_scores.median()) if valid_scores.notna().any() else 0.0,
        "global_score_std": float(valid_scores.std()) if valid_scores.notna().sum() > 1 else 0.0,
        "price_by_region": {},
        "cmpet_by_region": {},
        "region_scores": {},
    }
    for region_code, group in df.groupby("region_code"):
        stats["price_by_region"][str(region_code)] = pd.to_numeric(group["log_lttot_top_amount"], errors="coerce").dropna()
        stats["cmpet_by_region"][str(region_code)] = pd.to_numeric(group["log_cmpet_rate"], errors="coerce").dropna()
        latest = group.sort_values("announcement_date").tail(1).iloc[0]
        stats["region_scores"][str(region_code)] = {
            "lag1": float(latest["region_score_lag1"]),
            "roll5_mean": float(latest["region_score_roll5_mean"]),
            "roll5_std": float(latest["region_score_roll5_std"]),
        }
    return stats


def _percentile_rank(values: pd.Series, value: float) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    if clean.empty:
        return 0.5
    return float((clean <= value).mean())


def features_from_prediction_request(request: CutoffPredictionRequest) -> pd.DataFrame:
    stats = _feature_stats()
    region_code = str(request.region_code).strip()
    sale_price_log = float(np.log10(max(request.sale_price, 0) + 1))
    cmpet_log = float(np.log1p(max(request.competition_rate, 0)))
    region_scores = stats.get("region_scores", {}).get(region_code, {}) if stats else {}

    feature_row = {
        "log_cmpet_rate": cmpet_log,
        "SUPLY_HSHLDCO": request.general_supply_units,
        "spsply_ratio": 0,
        "SUBSCRPT_RANK_CODE": 1,
        "RESIDE_SECD": 1,
        "SPECLT_RDN_EARTH_AT": 0,
        "MDAT_TRGET_AREA_SECD": 0,
        "PARCPRC_ULS_AT": 0,
        "IMPRMN_BSNS_AT": 0,
        "PUBLIC_HOUSE_EARTH_AT": 0,
        "LRSCL_BLDLND_AT": 0,
        "NPLN_PRVOPR_PUBLIC_HOUSE_AT": 0,
        "log_lttot_top_amount": sale_price_log,
        "house_area": request.area_m2,
        "is_top_brand": int(any(brand in request.apartment_name for brand in TOP_BRANDS)),
        "price_rank_in_region": _percentile_rank(stats.get("price_by_region", {}).get(region_code, pd.Series(dtype=float)), sale_price_log)
        if stats
        else 0.5,
        "cmpet_rank_in_region": _percentile_rank(stats.get("cmpet_by_region", {}).get(region_code, pd.Series(dtype=float)), cmpet_log)
        if stats
        else 0.5,
        "region_score_lag1": region_scores.get("lag1", stats.get("global_score", 0) if stats else 0),
        "region_score_roll5_mean": region_scores.get("roll5_mean", stats.get("global_score", 0) if stats else 0),
        "region_score_roll5_std": region_scores.get("roll5_std", stats.get("global_score_std", 0) if stats else 0),
        "notice_year": request.supply_year,
        "notice_month": max(1, min(12, request.supply_quarter * 3)),
    }
    return pd.DataFrame([feature_row], columns=MODEL_FEATURE_COLUMNS)
