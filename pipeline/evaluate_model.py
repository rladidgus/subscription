import json
from pathlib import Path

from pipeline.common import PROJECT_ROOT


def evaluate_model() -> Path:
    metrics_path = PROJECT_ROOT / "model_artifacts" / "reports" / "metrics.json"
    metadata_path = PROJECT_ROOT / "model_artifacts" / "final" / "metadata.json"
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
