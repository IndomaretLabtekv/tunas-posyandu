"""Tests for dependency-light JSON tree inference."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from api.model import load_runtime_artifact, predict_runtime
from tabular.persist import load_artifact, predict


def test_json_tree_prediction_handles_numeric_and_missing_splits(tmp_path):
    artifact = {
        "artifact_version": 2,
        "objective": "binary sigmoid:1",
        "feature_names": ["x"],
        "feature_importance": [{"feature": "x", "importance": 1.0}],
        "tree_info": [
            {
                "tree_structure": {
                    "split_feature": 0,
                    "threshold": 1.0,
                    "decision_type": "<=",
                    "default_left": True,
                    "left_child": {"leaf_value": -1.0},
                    "right_child": {"leaf_value": 1.0},
                }
            }
        ],
    }
    path = tmp_path / "model.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    loaded = load_runtime_artifact(path)
    scores = predict_runtime(loaded, pd.DataFrame({"x": [0.0, 2.0, np.nan]}))

    assert np.allclose(
        scores,
        [1 / (1 + math.exp(1)), 1 / (1 + math.exp(-1)), 1 / (1 + math.exp(1))],
        atol=1e-15,
    )


def test_json_tree_prediction_rejects_missing_features(tmp_path):
    path = tmp_path / "model.json"
    path.write_text(
        json.dumps(
            {
                "artifact_version": 2,
                "objective": "binary sigmoid:1",
                "feature_names": ["required"],
                "feature_importance": [],
                "tree_info": [],
            }
        ),
        encoding="utf-8",
    )

    artifact = load_runtime_artifact(path)

    try:
        predict_runtime(artifact, pd.DataFrame({"other": [1.0]}))
    except ValueError as exc:
        assert "required" in str(exc)
    else:
        raise AssertionError("missing feature must be rejected")


def test_exported_runtime_predictions_match_training_artifact():
    frame = pd.read_csv("results/tabular/final/persistence_fixture.csv")
    expected = predict(
        load_artifact(Path("results/tabular/final/primary_model.joblib")),
        frame,
    )
    actual = predict_runtime(
        load_runtime_artifact(Path("results/tabular/final/primary_model.json")),
        frame,
    )

    assert np.allclose(actual, expected, rtol=0.0, atol=1e-12)
