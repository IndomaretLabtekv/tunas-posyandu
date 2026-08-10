"""Export the trusted LightGBM joblib artifact to dependency-light JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tabular.persist import load_artifact


def _validate_numeric_tree(node: dict) -> None:
    if "leaf_value" in node:
        return
    if node.get("decision_type") != "<=":
        raise ValueError(f"Runtime exporter only supports numeric splits, got {node.get('decision_type')}")
    _validate_numeric_tree(node["left_child"])
    _validate_numeric_tree(node["right_child"])


def build_runtime_artifact(training_artifact: dict) -> dict:
    model = training_artifact["model"]
    booster = model.booster_
    dumped = booster.dump_model()
    for tree in dumped["tree_info"]:
        _validate_numeric_tree(tree["tree_structure"])

    feature_names = list(training_artifact["feature_names"])
    gains = booster.feature_importance(importance_type="gain")
    total_gain = float(gains.sum())
    importance = [
        {"feature": feature, "importance": float(gain) / total_gain if total_gain else 0.0}
        for feature, gain in zip(feature_names, gains, strict=True)
    ]
    return {
        "artifact_version": 2,
        "objective": dumped["objective"],
        "feature_names": feature_names,
        "feature_importance": importance,
        "tree_info": dumped["tree_info"],
        "metadata": training_artifact["metadata"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results/tabular/final/primary_model.joblib"))
    parser.add_argument("--output", type=Path, default=Path("results/tabular/final/primary_model.json"))
    args = parser.parse_args()

    runtime_artifact = build_runtime_artifact(load_artifact(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(runtime_artifact, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
