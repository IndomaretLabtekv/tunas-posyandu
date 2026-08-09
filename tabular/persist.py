"""Simpan, muat, dan verifikasi artefak model tabular Tunas."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ARTIFACT_VERSION = 1
REQUIRED_METADATA = {
    "model_name", "model_version", "training_config", "seeds", "target",
    "created_utc", "git_commit",
}


def save_artifact(path: Path, model, feature_names: list[str], metadata: dict) -> None:
    missing = REQUIRED_METADATA - set(metadata)
    if missing:
        raise ValueError(f"Metadata model belum lengkap: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "artifact_version": ARTIFACT_VERSION,
        "model": model,
        "feature_names": list(feature_names),
        "metadata": metadata,
    }, path)


def load_artifact(path: Path) -> dict:
    artifact = joblib.load(path)
    required = {"artifact_version", "model", "feature_names", "metadata"}
    if not isinstance(artifact, dict) or required - set(artifact):
        raise ValueError(f"Artefak model tidak lengkap: {path}")
    if artifact["artifact_version"] != ARTIFACT_VERSION:
        raise ValueError(f"Versi artefak tidak didukung: {artifact['artifact_version']}")
    missing = REQUIRED_METADATA - set(artifact["metadata"])
    if missing:
        raise ValueError(f"Metadata model belum lengkap: {sorted(missing)}")
    return artifact


def predict(artifact: dict, frame: pd.DataFrame) -> np.ndarray:
    features = artifact["feature_names"]
    missing = set(features) - set(frame.columns)
    if missing:
        raise ValueError(f"Kolom fitur inferensi hilang: {sorted(missing)}")
    return artifact["model"].predict_proba(frame[features])[:, 1]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, type=Path)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    scores = predict(load_artifact(args.model), pd.read_csv(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"prediction": scores}).to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
