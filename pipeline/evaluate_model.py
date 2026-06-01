import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.common import PROJECT_ROOT
from pipeline.import_applyhome_csv import REGION_CODE_BY_NAME
from pipeline.model_features import MODEL_FEATURE_COLUMNS, MODEL_TARGET_COLUMN, load_or_build_model_feature_dataset


REPORTS_DIR = PROJECT_ROOT / "model_artifacts" / "reports"
FINAL_MODEL_DIR = PROJECT_ROOT / "model_artifacts" / "final"
REGION_PERFORMANCE_PATH = REPORTS_DIR / "region_performance.csv"


REGION_NAME_BY_CODE = {code: name for name, code in REGION_CODE_BY_NAME.items()}


def evaluate_model() -> Path:
    metrics_path = REPORTS_DIR / "metrics.json"
    metadata_path = FINAL_MODEL_DIR / "metadata.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metrics_path.write_text(
            json.dumps(metadata.get("results_summary", {}), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    elif not metrics_path.exists():
        metrics_path.write_text('{"rmse": null, "mae": null, "mape": null}\n', encoding="utf-8")
    return metrics_path


def _load_lightgbm():
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise RuntimeError("지역별 성능 리포트를 만들려면 lightgbm이 필요합니다.") from exc
    return lgb


def _predict_hurdle(features: pd.DataFrame) -> np.ndarray:
    lgb = _load_lightgbm()
    regressor_path = FINAL_MODEL_DIR / "lgb_tuned.txt"
    hurdle_path = FINAL_MODEL_DIR / "hurdle_classifier.txt"
    if not regressor_path.exists() or not hurdle_path.exists():
        raise FileNotFoundError("LightGBM Hurdle 모델 파일을 찾을 수 없습니다.")

    regressor = lgb.Booster(model_file=str(regressor_path))
    hurdle = lgb.Booster(model_file=str(hurdle_path))
    probabilities = hurdle.predict(features)
    regression_predictions = regressor.predict(features)
    predictions = np.where(probabilities < 0.5, 0, regression_predictions)
    return np.clip(predictions, 0, 84)


def _predict_hurdle_probability(features: pd.DataFrame) -> np.ndarray:
    lgb = _load_lightgbm()
    hurdle_path = FINAL_MODEL_DIR / "hurdle_classifier.txt"
    if not hurdle_path.exists():
        raise FileNotFoundError("LightGBM Hurdle 모델 파일을 찾을 수 없습니다.")
    hurdle = lgb.Booster(model_file=str(hurdle_path))
    return hurdle.predict(features)


def _predict_segment_soft(features: pd.DataFrame) -> np.ndarray:
    lgb = _load_lightgbm()
    classifier_path = FINAL_MODEL_DIR / "seg_classifier_30.txt"
    low_model_path = FINAL_MODEL_DIR / "seg_model_low.txt"
    high_model_path = FINAL_MODEL_DIR / "seg_model_high.txt"
    missing = [
        path.name
        for path in [classifier_path, low_model_path, high_model_path]
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(f"LightGBM Segment Soft 모델 파일을 찾을 수 없습니다: {', '.join(missing)}")

    classifier = lgb.Booster(model_file=str(classifier_path))
    low_model = lgb.Booster(model_file=str(low_model_path))
    high_model = lgb.Booster(model_file=str(high_model_path))
    high_probability = classifier.predict(features)
    if getattr(high_probability, "ndim", 1) > 1:
        high_probability = high_probability[:, -1]
    low_predictions = low_model.predict(features)
    high_predictions = high_model.predict(features)
    predictions = high_probability * high_predictions + (1 - high_probability) * low_predictions
    return np.clip(predictions, 0, 84)


def _predict_hybrid(features: pd.DataFrame) -> np.ndarray:
    competition_probabilities = _predict_hurdle_probability(features)
    segment_predictions = _predict_segment_soft(features)
    predictions = np.where(competition_probabilities < 0.5, 0, segment_predictions)
    return np.clip(predictions, 0, 84)


def _mae(actual: pd.Series, predicted: pd.Series) -> float:
    if actual.empty:
        return np.nan
    return float((predicted - actual).abs().mean())


def _rmse(actual: pd.Series, predicted: pd.Series) -> float:
    if actual.empty:
        return np.nan
    return float(np.sqrt(((predicted - actual) ** 2).mean()))


def _rounded(value: float) -> float:
    if pd.isna(value):
        return np.nan
    return round(float(value), 4)


def _confidence(best_mae: float) -> tuple[str, str, str]:
    if best_mae <= 5:
        return "high", "높음", "지역별 평균 오차가 5점 이하라 비교적 안정적인 구간입니다."
    if best_mae <= 8:
        return "medium", "보통", "지역별 평균 오차가 5~8점 수준이라 여유 점수를 두고 해석해야 합니다."
    return "low", "낮음", "지역별 평균 오차가 8점을 넘어 보수적으로 해석해야 합니다."


def evaluate_region_performance() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_or_build_model_feature_dataset()
    df[MODEL_TARGET_COLUMN] = pd.to_numeric(df[MODEL_TARGET_COLUMN], errors="coerce")
    valid = df.dropna(subset=[MODEL_TARGET_COLUMN]).copy()
    if valid.empty:
        raise ValueError("지역별 성능을 계산할 유효한 LWET_SCORE가 없습니다.")

    features = valid[MODEL_FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce").fillna(0)
    valid["hurdle_predicted_score"] = _predict_hurdle(features)
    valid["segment_soft_predicted_score"] = _predict_segment_soft(features)
    valid["hybrid_predicted_score"] = _predict_hybrid(features)

    rows = []
    for region_code, group in valid.groupby("region_code"):
        nonzero = group[group[MODEL_TARGET_COLUMN] > 0]
        hurdle_mae_all = _mae(group[MODEL_TARGET_COLUMN], group["hurdle_predicted_score"])
        segment_mae_all = _mae(group[MODEL_TARGET_COLUMN], group["segment_soft_predicted_score"])
        hybrid_mae_all = _mae(group[MODEL_TARGET_COLUMN], group["hybrid_predicted_score"])
        hurdle_mae_nonzero = _mae(nonzero[MODEL_TARGET_COLUMN], nonzero["hurdle_predicted_score"])
        segment_mae_nonzero = _mae(nonzero[MODEL_TARGET_COLUMN], nonzero["segment_soft_predicted_score"])
        hybrid_mae_nonzero = _mae(nonzero[MODEL_TARGET_COLUMN], nonzero["hybrid_predicted_score"])
        all_scores = {
            "hurdle": hurdle_mae_all,
            "segment_soft": segment_mae_all,
            "hybrid": hybrid_mae_all,
        }
        nonzero_scores = {
            "hurdle": hurdle_mae_nonzero,
            "segment_soft": segment_mae_nonzero,
            "hybrid": hybrid_mae_nonzero,
        }
        best_model = min(all_scores, key=all_scores.get)
        best_mae = all_scores[best_model]
        best_model_nonzero = min(nonzero_scores, key=nonzero_scores.get)
        best_mae_nonzero = nonzero_scores[best_model_nonzero]
        confidence_level, confidence_label, confidence_note = _confidence(best_mae)
        rows.append(
            {
                "region_code": str(region_code),
                "region_name": REGION_NAME_BY_CODE.get(str(region_code), ""),
                "actual_count": int(len(group)),
                "zero_actual_count": int((group[MODEL_TARGET_COLUMN] == 0).sum()),
                "nonzero_actual_count": int((group[MODEL_TARGET_COLUMN] > 0).sum()),
                "zero_actual_rate": _rounded((group[MODEL_TARGET_COLUMN] == 0).mean()),
                "mae": _rounded(hurdle_mae_all),
                "rmse": _rounded(_rmse(group[MODEL_TARGET_COLUMN], group["hurdle_predicted_score"])),
                "mean_actual_score": round(float(group[MODEL_TARGET_COLUMN].mean()), 4),
                "mean_predicted_score": round(float(group["hurdle_predicted_score"].mean()), 4),
                "hurdle_mae_all": _rounded(hurdle_mae_all),
                "hurdle_rmse_all": _rounded(_rmse(group[MODEL_TARGET_COLUMN], group["hurdle_predicted_score"])),
                "hurdle_mae_nonzero": _rounded(hurdle_mae_nonzero),
                "hurdle_rmse_nonzero": _rounded(_rmse(nonzero[MODEL_TARGET_COLUMN], nonzero["hurdle_predicted_score"])),
                "hurdle_region_bias": _rounded(group[MODEL_TARGET_COLUMN].mean() - group["hurdle_predicted_score"].mean()),
                "hurdle_mean_predicted_score": _rounded(group["hurdle_predicted_score"].mean()),
                "segment_soft_mae_all": _rounded(segment_mae_all),
                "segment_soft_rmse_all": _rounded(_rmse(group[MODEL_TARGET_COLUMN], group["segment_soft_predicted_score"])),
                "segment_soft_mae_nonzero": _rounded(segment_mae_nonzero),
                "segment_soft_rmse_nonzero": _rounded(_rmse(nonzero[MODEL_TARGET_COLUMN], nonzero["segment_soft_predicted_score"])),
                "segment_soft_region_bias": _rounded(
                    group[MODEL_TARGET_COLUMN].mean() - group["segment_soft_predicted_score"].mean()
                ),
                "segment_soft_mean_predicted_score": _rounded(group["segment_soft_predicted_score"].mean()),
                "hybrid_mae_all": _rounded(hybrid_mae_all),
                "hybrid_rmse_all": _rounded(_rmse(group[MODEL_TARGET_COLUMN], group["hybrid_predicted_score"])),
                "hybrid_mae_nonzero": _rounded(hybrid_mae_nonzero),
                "hybrid_rmse_nonzero": _rounded(_rmse(nonzero[MODEL_TARGET_COLUMN], nonzero["hybrid_predicted_score"])),
                "hybrid_region_bias": _rounded(group[MODEL_TARGET_COLUMN].mean() - group["hybrid_predicted_score"].mean()),
                "hybrid_mean_predicted_score": _rounded(group["hybrid_predicted_score"].mean()),
                "best_model_all": best_model,
                "best_mae_all": _rounded(best_mae),
                "best_model_nonzero": best_model_nonzero,
                "best_mae_nonzero": _rounded(best_mae_nonzero),
                "confidence_level": confidence_level,
                "confidence_label": confidence_label,
                "confidence_note": confidence_note,
            }
        )

    report = pd.DataFrame(rows).sort_values(["actual_count", "region_code"], ascending=[False, True])
    report.to_csv(REGION_PERFORMANCE_PATH, index=False)
    return REGION_PERFORMANCE_PATH


if __name__ == "__main__":
    print(evaluate_model())
    print(evaluate_region_performance())
