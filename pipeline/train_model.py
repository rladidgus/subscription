from pathlib import Path

from pipeline.common import PROJECT_ROOT
from pipeline.model_features import build_applyhome_model_features


def train_model() -> Path:
    model_path = PROJECT_ROOT / "model_artifacts" / "final" / "lgb_tuned.txt"
    if model_path.exists():
        return model_path
    return build_applyhome_model_features()
