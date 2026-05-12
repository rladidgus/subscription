from pathlib import Path

from pipeline.common import PROJECT_ROOT


def train_model() -> Path:
    artifact_path = PROJECT_ROOT / "model_artifacts" / "artifacts" / "cutoff_random_forest.joblib"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    return artifact_path
