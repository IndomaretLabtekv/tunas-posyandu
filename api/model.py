"""Muat artefak model prioritisasi secara malas."""

from __future__ import annotations

import os
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tabular.explain import Explainer
from tabular.persist import load_artifact, predict

# ponytail: SHAP memberi warning API change yang diketahui untuk LightGBM biner.
warnings.filterwarnings("ignore", category=UserWarning, module="shap.explainers._tree")

DEFAULT_MODEL_PATH = "results/tabular/final/primary_model.joblib"


class ModelNotLoadedError(RuntimeError):
    """Model belum tersedia atau gagal dimuat."""


@lru_cache(maxsize=1)
def _load_artifact_cached(path: str) -> dict[str, Any]:
    return load_artifact(Path(path))


def get_model_path() -> str:
    return os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)


def get_artifact() -> dict[str, Any] | None:
    """Muat artefak model; kembalikan None bila file tidak ada."""
    path = get_model_path()
    if not Path(path).exists():
        return None
    return _load_artifact_cached(path)


def predict_scores(frame: pd.DataFrame) -> np.ndarray:
    """Prediksi probabilitas risiko untuk setiap baris."""
    art = get_artifact()
    if art is None:
        raise ModelNotLoadedError("model artifact tidak ditemukan")
    return predict(art, frame)


def explain_row(frame: pd.DataFrame, row_index, top_k: int = 5) -> list[dict[str, Any]]:
    """SHAP attribution untuk satu baris."""
    art = get_artifact()
    if art is None:
        raise ModelNotLoadedError("model artifact tidak ditemukan")
    explainer = Explainer(art["model"], art["feature_names"])
    return [a.as_dict() for a in explainer.explain_child(frame, row_index, top_k=top_k)]


def rank_scores(scores: np.ndarray, tie_break: list[str]) -> np.ndarray:
    """Peringkat 1..N deterministik: skor tinggi dulu, tie-break lexicographic."""
    order = np.lexsort((np.asarray(tie_break).astype(str), -np.asarray(scores, dtype=float)))
    ranks = np.empty(len(scores), dtype=int)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks
