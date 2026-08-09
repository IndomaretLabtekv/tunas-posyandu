"""Focused correctness checks for the final tabular closure audits."""

import numpy as np
import pandas as pd
import pytest

from tabular.closure import _compare_csv, benchmark_batches, perturb_raw_history, scenario_seed
from tabular.evaluate import boundary_tie_sensitivity, capacity_predictions
from tabular.features import build_features


def test_tie_bounds_without_boundary_tie_equal_observed():
    result = boundary_tie_sensitivity(
        [1, 0, 1, 0], [0.9, 0.8, 0.7, 0.6], 0.5, ["A", "B", "C", "D"]
    )
    assert result["n_score_equal_cutoff"] == 1
    assert result["min_tp"] == result["observed_tp"] == result["max_tp"] == 1


def test_tie_bounds_all_cutoff_candidates_negative():
    result = boundary_tie_sensitivity(
        [1, 0, 0, 0], [0.9, 0.8, 0.8, 0.1], 0.5, ["A", "B", "C", "D"]
    )
    assert result["positive_in_tie_group"] == 0
    assert result["min_tp"] == result["max_tp"] == 1


def test_tie_bounds_all_cutoff_candidates_positive():
    result = boundary_tie_sensitivity(
        [0, 1, 1, 0], [0.9, 0.8, 0.8, 0.1], 0.5, ["A", "B", "C", "D"]
    )
    assert result["positive_in_tie_group"] == 2
    assert result["min_tp"] == result["max_tp"] == 1


def test_tie_bounds_mixed_group_with_fewer_slots_than_candidates():
    result = boundary_tie_sensitivity(
        [1, 1, 0, 1, 0, 0],
        [0.9, 0.8, 0.8, 0.8, 0.8, 0.1],
        0.5,
        ["A", "B", "C", "D", "E", "F"],
    )
    assert result["slots_taken_from_tie"] == 2
    assert result["min_tp"] == 1
    assert result["max_tp"] == 3
    assert result["min_recall_at_k"] == pytest.approx(1 / 3)
    assert result["max_recall_at_k"] == 1.0


def test_tie_audit_keeps_exact_k_and_production_membership_unchanged():
    scores = np.array([0.9, 0.8, 0.8, 0.8, 0.1])
    ids = np.array(["C5", "C3", "C1", "C2", "C4"])
    before = capacity_predictions(scores, 0.4, ids)
    boundary_tie_sensitivity([1, 0, 1, 0, 0], scores, 0.4, ids)
    after = capacity_predictions(scores, 0.4, ids)
    assert before.sum() == 2
    np.testing.assert_array_equal(before, after)
    assert set(ids[after.astype(bool)]) == {"C5", "C1"}


def test_tie_audit_requires_production_tie_break():
    with pytest.raises(ValueError, match="tie_break"):
        boundary_tie_sensitivity([1, 0], [0.5, 0.5], 0.5, None)


def _raw_fixture():
    return pd.DataFrame({
        "child_id": ["A", "A", "A", "B", "B", "B"],
        "visit_date": pd.to_datetime([
            "2025-01-01", "2025-02-01", "2025-03-01",
            "2025-01-02", "2025-02-02", "2025-03-02",
        ]),
        "age_days": [100, 131, 159, 100, 131, 159],
        "sex": ["M", "M", "M", "F", "F", "F"],
        "length_cm": [60.0, 61.0, 62.0, 59.0, 60.0, 61.0],
        "haz": [-1.0, -1.1, -1.2, -1.0, -1.1, -1.2],
    })


def test_targeted_feature_build_matches_full_pipeline():
    raw = _raw_fixture()
    full = build_features(raw)
    targeted = build_features(raw, output_indices=[1, 4])
    pd.testing.assert_frame_equal(targeted, full.loc[[1, 4]])


def test_perturbation_never_changes_future_measurements():
    raw = _raw_fixture()
    X_test = pd.DataFrame({
        "child_id": ["A", "B"],
        "prediction_date": pd.to_datetime(["2025-02-01", "2025-02-02"]),
    }, index=[1, 4])
    perturbed, metadata = perturb_raw_history(
        raw, X_test,
        generator_seed=42,
        scenario="length_noise_sigma_1_0cm",
        kind="length_noise_cm",
        level=1.0,
    )
    pd.testing.assert_series_equal(perturbed.loc[[2, 5], "length_cm"], raw.loc[[2, 5], "length_cm"])
    pd.testing.assert_series_equal(perturbed.loc[[2, 5], "haz"], raw.loc[[2, 5], "haz"])
    assert metadata["causal_timing_verified"]


def test_current_measurement_missing_preserves_past_and_future():
    raw = _raw_fixture()
    X_test = pd.DataFrame({
        "child_id": ["A", "B"],
        "prediction_date": pd.to_datetime(["2025-02-01", "2025-02-02"]),
    }, index=[1, 4])
    perturbed, _ = perturb_raw_history(
        raw, X_test,
        generator_seed=42,
        scenario="current_measurement_missing",
        kind="current_measurement_missing",
        level=1.0,
    )
    assert perturbed.loc[[1, 4], ["length_cm", "haz"]].isna().all().all()
    pd.testing.assert_series_equal(perturbed.loc[[0, 2, 3, 5], "length_cm"], raw.loc[[0, 2, 3, 5], "length_cm"])


def test_scenario_seed_is_stable_and_scenario_specific():
    assert scenario_seed(42, "a") == scenario_seed(42, "a")
    assert scenario_seed(42, "a") != scenario_seed(42, "b")


def test_benchmark_batches_preserve_schema_and_order():
    frame = pd.DataFrame({
        "child_id": ["C2", "C1", "C3"],
        "prediction_date": pd.to_datetime(["2025-01-02", "2025-01-01", "2025-01-03"]),
        "a": [2.0, 1.0, 3.0],
        "b": [5.0, 4.0, 6.0],
    }, index=[20, 10, 30])
    batches = benchmark_batches(frame, ["a", "b"], (1, 3))
    assert list(batches[1]["child_id"]) == ["C1"]
    assert list(batches[3].index) == [10, 20, 30]
    assert {"a", "b"}.issubset(batches[3].columns)


def test_reproduction_comparison_handles_boolean_columns(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    pd.DataFrame({"flag": [True, False], "value": [1.0, 2.0]}).to_csv(a, index=False)
    pd.DataFrame({"flag": [True, False], "value": [1.0, 2.0]}).to_csv(b, index=False)
    result = _compare_csv(a, b, 1e-12)
    assert result["numeric_equal"]
