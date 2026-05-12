from pathlib import Path

from pipeline.common import PROJECT_ROOT


def evaluate_model() -> Path:
    metrics_path = PROJECT_ROOT / "model_artifacts" / "reports" / "metrics.json"
    if not metrics_path.exists():
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text('{"rmse": null, "mae": null, "mape": null}\n', encoding="utf-8")
    return metrics_path
