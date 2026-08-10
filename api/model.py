"""Load and evaluate the dependency-light runtime tree artifact."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tabular.explain import label_for

DEFAULT_MODEL_PATH = "results/tabular/final/primary_model.json"
RUNTIME_ARTIFACT_VERSION = 2


class ModelNotLoadedError(RuntimeError):
    """Raised when the runtime model is unavailable."""


def load_runtime_artifact(path: Path) -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    required = {"artifact_version", "objective", "feature_names", "tree_info", "feature_importance"}
    if not isinstance(artifact, dict) or required - set(artifact):
        raise ValueError(f"Artefak runtime tidak lengkap: {path}")
    if artifact["artifact_version"] != RUNTIME_ARTIFACT_VERSION:
        raise ValueError(f"Versi artefak runtime tidak didukung: {artifact['artifact_version']}")
    if not str(artifact["objective"]).startswith("binary"):
        raise ValueError("Hanya objective binary LightGBM yang didukung")
    return artifact


@lru_cache(maxsize=1)
def _load_artifact_cached(path: str) -> dict[str, Any]:
    return load_runtime_artifact(Path(path))


def get_model_path() -> str:
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


def get_artifact() -> dict[str, Any] | None:
    path = get_model_path()
    if not Path(path).exists():
        return None
    return _load_artifact_cached(path)


def _tree_value(tree: dict[str, Any], row: np.ndarray) -> float:
    node = tree["tree_structure"]
    while "leaf_value" not in node:
        if node.get("decision_type") != "<=":
            raise ValueError(f"Split LightGBM tidak didukung: {node.get('decision_type')}")
        value = row[int(node["split_feature"])]
        go_left = bool(node["default_left"]) if np.isnan(value) else value <= float(node["threshold"])
        node = node["left_child"] if go_left else node["right_child"]
    return float(node["leaf_value"])


def predict_runtime(artifact: dict[str, Any], frame: pd.DataFrame) -> np.ndarray:
    features = list(artifact["feature_names"])
    missing = set(features) - set(frame.columns)
    if missing:
        raise ValueError(f"Kolom fitur inferensi hilang: {sorted(missing)}")

    matrix = frame[features].to_numpy(dtype=float)
    raw_scores = np.fromiter(
        (sum(_tree_value(tree, row) for tree in artifact["tree_info"]) for row in matrix),
        dtype=float,
        count=len(matrix),
    )
    return 1.0 / (1.0 + np.exp(-np.clip(raw_scores, -709.0, 709.0)))


def predict_scores(frame: pd.DataFrame) -> np.ndarray:
    artifact = get_artifact()
    if artifact is None:
        raise ModelNotLoadedError("model artifact tidak ditemukan")
    return predict_runtime(artifact, frame)


def explain_row(frame: pd.DataFrame, row_index, top_k: int = 5) -> list[dict[str, Any]]:
    artifact = get_artifact()
    if artifact is None:
        raise ModelNotLoadedError("model artifact tidak ditemukan")
    if row_index not in frame.index:
        raise KeyError(f"Baris {row_index!r} tidak ada")

    row = frame.loc[row_index]
    importance = sorted(
        artifact["feature_importance"],
        key=lambda item: (-float(item["importance"]), str(item["feature"])),
    )[:top_k]
    return [
        {
            "feature": item["feature"],
            "label": label_for(item["feature"]),
            "value": None if pd.isna(row[item["feature"]]) else round(float(row[item["feature"]]), 3),
            "importance": round(float(item["importance"]), 6),
        }
        for item in importance
    ]


def rank_scores(scores: np.ndarray, tie_break: list[str]) -> np.ndarray:
    order = np.lexsort((np.asarray(tie_break).astype(str), -np.asarray(scores, dtype=float)))
    ranks = np.empty(len(scores), dtype=int)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks
