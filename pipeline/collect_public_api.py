from pathlib import Path
import os
import re
from typing import Any
from urllib.parse import unquote

import httpx
import pandas as pd
from dotenv import load_dotenv

from pipeline.common import RAW_DIR, ensure_data_dirs, read_sample_training_dataset, write_csv


load_dotenv()

DETAIL_API_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1"
COMPETITION_API_BASE_URL = "https://api.odcloud.kr/api/ApplyhomeInfoCmpetRtSvc/v1"
APT_DETAIL_ENDPOINT = "getAPTLttotPblancDetail"
APT_MODEL_ENDPOINT = "getAPTLttotPblancMdl"
APT_COMPETITION_ENDPOINT = "getAPTLttotPblancCmpet"
APT_SPECIAL_SUPPLY_ENDPOINT = "getAPTSpsplyReqstStus"
OUTPUT_PATH = RAW_DIR / "public_api" / "public_apartment_supply.csv"
COMPETITION_OUTPUT_PATH = RAW_DIR / "public_api" / "apt_competition.csv"
SPECIAL_SUPPLY_OUTPUT_PATH = RAW_DIR / "public_api" / "apt_special_supply_status.csv"


def _to_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    normalized = str(value).replace(",", "").strip()
    try:
        return float(normalized)
    except ValueError:
        matched = re.search(r"\d+(?:\.\d+)?", normalized)
        if matched:
            return float(matched.group())
        return default


def _fetch_odcloud_rows(
    endpoint: str,
    service_key: str,
    *,
    base_url: str = DETAIL_API_BASE_URL,
    page: int = 1,
    per_page: int = 100,
    params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    request_params = {
        "page": page,
        "perPage": per_page,
        "returnType": "JSON",
        "serviceKey": unquote(service_key),
    }
    if params:
        request_params.update(params)

    response = httpx.get(
        f"{base_url}/{endpoint}",
        params=request_params,
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data", [])


def parse_public_api_rows(
    detail_rows: list[dict[str, Any]],
    model_rows: list[dict[str, Any]] | None = None,
    competition_rows: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    model_rows = model_rows or []
    competition_rows = competition_rows or []
    model_by_house = {
        (str(row.get("HOUSE_MANAGE_NO", "")), str(row.get("PBLANC_NO", ""))): row
        for row in model_rows
    }
    competition_by_house: dict[tuple[str, str], float] = {}
    for row in competition_rows:
        key = (str(row.get("HOUSE_MANAGE_NO", "")), str(row.get("PBLANC_NO", "")))
        competition_by_house[key] = max(
            competition_by_house.get(key, 0.0),
            _to_float(row.get("CMPET_RATE")),
        )
    records: list[dict[str, Any]] = []

    for row in detail_rows:
        house_manage_no = str(row.get("HOUSE_MANAGE_NO", ""))
        pblanc_no = str(row.get("PBLANC_NO", ""))
        model = model_by_house.get((house_manage_no, pblanc_no), {})
        announcement_date = row.get("RCRIT_PBLANC_DE") or row.get("RCRIT_PBLANC_DE_NM") or ""
        announcement = pd.to_datetime(announcement_date, errors="coerce")

        records.append(
            {
                "apartment_id": house_manage_no or pblanc_no or row.get("HOUSE_NM", ""),
                "apartment_name": row.get("HOUSE_NM", ""),
                "region_code": str(row.get("SUBSCRPT_AREA_CODE", "")),
                "region_name": row.get("SUBSCRPT_AREA_CODE_NM", ""),
                "announcement_date": announcement.strftime("%Y-%m-%d") if not pd.isna(announcement) else "",
                "supply_year": int(announcement.year) if not pd.isna(announcement) else 0,
                "supply_quarter": int(announcement.quarter) if not pd.isna(announcement) else 0,
                "general_supply_units": _to_int(
                    model.get("SUPLY_HSHLDCO")
                    or row.get("TOT_SUPLY_HSHLDCO")
                    or row.get("SUPLY_HSHLDCO")
                ),
                "sale_price": _to_float(model.get("LTTOT_TOP_AMOUNT") or row.get("LTTOT_TOP_AMOUNT")),
                "competition_rate": competition_by_house.get((house_manage_no, pblanc_no), 0.0),
                "area_m2": _to_float(model.get("HOUSE_TY") or model.get("EXCLUSE_AR")),
            }
        )

    return pd.DataFrame(records)


def parse_competition_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records = [
        {
            "house_manage_no": str(row.get("HOUSE_MANAGE_NO", "")),
            "pblanc_no": str(row.get("PBLANC_NO", "")),
            "house_type": row.get("HOUSE_TY", ""),
            "model_no": row.get("MODEL_NO", ""),
            "reside_name": row.get("RESIDE_SENM") or row.get("RESIDNT_PRIOR_SENM") or "",
            "subscription_rank": row.get("SUBSCRPT_RANK_CODE", ""),
            "supply_units": _to_int(row.get("SUPLY_HSHLDCO")),
            "request_count": _to_int(row.get("REQ_CNT")),
            "competition_rate": _to_float(row.get("CMPET_RATE")),
        }
        for row in rows
    ]
    return pd.DataFrame(records)


def parse_special_supply_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for row in rows:
        count_items = {
            key: _to_int(value)
            for key, value in row.items()
            if key.endswith("_CNT")
        }
        records.append(
            {
                "house_manage_no": str(row.get("HOUSE_MANAGE_NO", "")),
                "pblanc_no": str(row.get("PBLANC_NO", "")),
                "house_type": row.get("HOUSE_TY", ""),
                "model_no": row.get("MODEL_NO", ""),
                "total_special_request_count": sum(count_items.values()),
                **count_items,
            }
        )
    return pd.DataFrame(records)


def _sample_public_api_dataframe() -> pd.DataFrame:
    sample = read_sample_training_dataset()
    columns = [
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
        "area_m2",
    ]
    return sample[columns]


def _sample_competition_dataframe() -> pd.DataFrame:
    sample = read_sample_training_dataset()
    return pd.DataFrame(
        {
            "house_manage_no": sample["apartment_id"],
            "pblanc_no": sample["apartment_id"],
            "house_type": sample["area_m2"],
            "model_no": "",
            "reside_name": sample["region_name"],
            "subscription_rank": "1",
            "supply_units": sample["general_supply_units"],
            "request_count": (sample["general_supply_units"] * sample["competition_rate"]).round().astype(int),
            "competition_rate": sample["competition_rate"],
        }
    )


def _sample_special_supply_dataframe() -> pd.DataFrame:
    sample = read_sample_training_dataset()
    return pd.DataFrame(
        {
            "house_manage_no": sample["apartment_id"],
            "pblanc_no": sample["apartment_id"],
            "house_type": sample["area_m2"],
            "model_no": "",
            "total_special_request_count": 0,
        }
    )


def collect_competition_api(use_fallback: bool = True) -> Path:
    ensure_data_dirs()
    service_key = os.getenv("PUBLIC_DATA_COMPETITION_API_KEY", "")
    if not service_key:
        if not use_fallback:
            raise RuntimeError("PUBLIC_DATA_COMPETITION_API_KEY가 설정되어 있지 않습니다.")
        if COMPETITION_OUTPUT_PATH.exists():
            return COMPETITION_OUTPUT_PATH
        return write_csv(_sample_competition_dataframe(), COMPETITION_OUTPUT_PATH)

    try:
        rows = _fetch_odcloud_rows(
            APT_COMPETITION_ENDPOINT,
            service_key,
            base_url=COMPETITION_API_BASE_URL,
        )
        df = parse_competition_rows(rows)
        if df.empty and use_fallback:
            df = _sample_competition_dataframe()
    except httpx.HTTPError:
        if not use_fallback:
            raise
        if COMPETITION_OUTPUT_PATH.exists():
            return COMPETITION_OUTPUT_PATH
        df = _sample_competition_dataframe()

    return write_csv(df, COMPETITION_OUTPUT_PATH)


def collect_special_supply_api(use_fallback: bool = True) -> Path:
    ensure_data_dirs()
    service_key = os.getenv("PUBLIC_DATA_COMPETITION_API_KEY", "")
    if not service_key:
        if not use_fallback:
            raise RuntimeError("PUBLIC_DATA_COMPETITION_API_KEY가 설정되어 있지 않습니다.")
        if SPECIAL_SUPPLY_OUTPUT_PATH.exists():
            return SPECIAL_SUPPLY_OUTPUT_PATH
        return write_csv(_sample_special_supply_dataframe(), SPECIAL_SUPPLY_OUTPUT_PATH)

    try:
        rows = _fetch_odcloud_rows(
            APT_SPECIAL_SUPPLY_ENDPOINT,
            service_key,
            base_url=COMPETITION_API_BASE_URL,
        )
        df = parse_special_supply_rows(rows)
        if df.empty and use_fallback:
            df = _sample_special_supply_dataframe()
    except httpx.HTTPError:
        if not use_fallback:
            raise
        if SPECIAL_SUPPLY_OUTPUT_PATH.exists():
            return SPECIAL_SUPPLY_OUTPUT_PATH
        df = _sample_special_supply_dataframe()

    return write_csv(df, SPECIAL_SUPPLY_OUTPUT_PATH)


def collect_public_api(use_fallback: bool = True) -> Path:
    ensure_data_dirs()
    service_key = os.getenv("PUBLIC_DATA_API_KEY", "")
    if not service_key:
        if not use_fallback:
            raise RuntimeError("PUBLIC_DATA_API_KEY가 설정되어 있지 않습니다.")
        if OUTPUT_PATH.exists():
            return OUTPUT_PATH
        return write_csv(_sample_public_api_dataframe(), OUTPUT_PATH)

    try:
        detail_rows = _fetch_odcloud_rows(APT_DETAIL_ENDPOINT, service_key)
        model_rows = _fetch_odcloud_rows(APT_MODEL_ENDPOINT, service_key)
        competition_key = os.getenv("PUBLIC_DATA_COMPETITION_API_KEY", "")
        competition_rows = (
            _fetch_odcloud_rows(
                APT_COMPETITION_ENDPOINT,
                competition_key,
                base_url=COMPETITION_API_BASE_URL,
            )
            if competition_key
            else []
        )
        df = parse_public_api_rows(detail_rows, model_rows, competition_rows)
        write_csv(parse_competition_rows(competition_rows), COMPETITION_OUTPUT_PATH)
        collect_special_supply_api(use_fallback=use_fallback)
        if df.empty and use_fallback:
            df = _sample_public_api_dataframe()
    except httpx.HTTPError:
        if not use_fallback:
            raise
        if OUTPUT_PATH.exists():
            return OUTPUT_PATH
        df = _sample_public_api_dataframe()

    return write_csv(df, OUTPUT_PATH)


if __name__ == "__main__":
    print(collect_public_api())
