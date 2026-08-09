"""Closure audits for tabular tie sensitivity, robustness, and latency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from data.generate_synth import SynthConfig, generate
from tabular.evaluate import (
    boundary_tie_sensitivity,
    capacity_predictions,
    evaluate_ranking,
)
from tabular.features import build_dataset, feature_columns
from tabular.final_experiment import _markdown_table, load_config
from tabular.persist import load_artifact, predict as predict_artifact
from tabular.splits import assert_no_child_leakage, grouped_split, temporal_split
from tabular.train import ExperimentConfig, load_dataset, prepare, run, select_index_visits
from tabular.who_lms import haz_series

PRIMARY_MODEL = "M2_plus_trajectory"
SCENARIOS = (
    ("baseline", "none", 0.0),
    ("length_noise_sigma_0_5cm", "length_noise_cm", 0.5),
    ("length_noise_sigma_1_0cm", "length_noise_cm", 1.0),
    ("length_noise_sigma_2_0cm", "length_noise_cm", 2.0),
    ("length_missing_plus_10pct", "length_missing_fraction", 0.10),
    ("length_missing_plus_20pct", "length_missing_fraction", 0.20),
    ("length_missing_plus_30pct", "length_missing_fraction", 0.30),
    ("current_measurement_missing", "current_measurement_missing", 1.0),
)
ROBUSTNESS_METRICS = (
    "auprc",
    "recall@5%", "recall@10%", "recall@20%",
    "precision@5%", "precision@10%", "precision@20%",
    "lift@5%", "lift@10%", "lift@20%",
    "n_intended", "n_scored", "coverage",
    "delta_auprc", "delta_recall@20%", "delta_precision@20%", "delta_lift@20%",
)


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _git_dirty() -> bool:
    return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _model_fingerprint(artifact: dict) -> str:
    """Stable fingerprint excluding joblib metadata timestamps and file framing."""
    booster_text = artifact["model"].booster_.model_to_string()
    payload = json.dumps(artifact["feature_names"], separators=(",", ":")) + booster_text
    return hashlib.sha256(payload.encode()).hexdigest()


def scenario_seed(generator_seed: int, scenario: str) -> int:
    """Stable seed independent of Python's randomized ``hash()``."""
    raw = hashlib.sha256(f"{generator_seed}:{scenario}".encode()).digest()
    return int.from_bytes(raw[:8], "little") % (2**32)


def _ensure_cohort(cfg: dict, seed: int) -> Path:
    path = Path(cfg["data_dir"]) / f"{cfg['dataset_version']}_seed_{seed}.csv"
    if path.exists():
        return path
    synth_cfg = SynthConfig(n_children=int(cfg["n_children"]), seed=int(seed))
    cohort = generate(synth_cfg)
    cohort["haz"] = haz_series(cohort)
    path.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_csv(path, index=False)
    path.with_suffix(".config.json").write_text(
        json.dumps(asdict(synth_cfg), indent=2), encoding="utf-8"
    )
    return path


def _test_indices(X: pd.DataFrame, evaluation: str, seed: int) -> pd.Index:
    if evaluation == "grouped":
        split = grouped_split(X, seed=seed)
        assert_no_child_leakage(split)
    elif evaluation == "temporal":
        split = temporal_split(
            X,
            date_col="prediction_date",
            seed=seed,
            label_available_col="label_available_date",
        )
    else:
        raise ValueError(f"evaluation tidak dikenal: {evaluation!r}")
    return select_index_visits(X.loc[split.test], evaluation)


def load_contexts(cfg: dict) -> list[dict]:
    """Load frozen per-seed models, training only when ignored run files are absent."""
    contexts = []
    reference_path = Path(cfg["output_dir"]) / "per_seed_metrics.csv"
    reference = pd.read_csv(reference_path) if reference_path.exists() else None
    expected_features = feature_columns(["snapshot", "trajectory"])

    for seed in cfg["seeds"]:
        data_path = _ensure_cohort(cfg, int(seed))
        raw = load_dataset(data_path)
        X, y, _ = prepare(raw)
        for evaluation in cfg["splits"]:
            run_dir = Path(cfg["output_dir"]) / "runs" / f"seed_{seed}" / evaluation
            model_path = run_dir / "primary_model.joblib"
            if model_path.exists():
                test_idx = _test_indices(X, evaluation, int(seed))
                X_test, y_test = X.loc[test_idx], y.loc[test_idx]
                artifact = load_artifact(model_path)
            else:
                result = run(ExperimentConfig(
                    data_path=data_path,
                    out_dir=run_dir,
                    seed=int(seed),
                    split_kind=evaluation,
                    k_fractions=tuple(cfg["k_fractions"]),
                    operating_k=float(cfg["operating_k"]),
                    primary_model=cfg["primary_model"],
                ))
                X_test, y_test = result["X_test"], result["y_test"]
                artifact = load_artifact(result["model_path"])
            if artifact["metadata"]["model_name"] != PRIMARY_MODEL:
                raise AssertionError(f"Bukan artefak M2: {model_path}")
            if artifact["feature_names"] != expected_features:
                raise AssertionError(f"Urutan fitur M2 berubah: {model_path}")
            scores = predict_artifact(artifact, X_test)
            metrics = evaluate_ranking(
                y_test,
                scores,
                tuple(cfg["k_fractions"]),
                X_test["child_id"].to_numpy(),
            )
            if reference is not None:
                row = reference[
                    reference["generator_seed"].eq(seed)
                    & reference["evaluation"].eq(evaluation)
                    & reference["model"].eq(PRIMARY_MODEL)
                ]
                if len(row) != 1:
                    raise AssertionError("Baris referensi M2 final tidak unik.")
                for metric in ("auprc", "recall@5%", "recall@10%", "recall@20%"):
                    if not np.isclose(metrics[metric], float(row.iloc[0][metric]), atol=5e-5):
                        raise AssertionError(
                            f"Skor frozen {seed}/{evaluation}/{metric} tidak cocok dengan final."
                        )
            contexts.append({
                "seed": int(seed),
                "evaluation": evaluation,
                "raw": raw,
                "X_test": X_test,
                "y_test": y_test,
                "artifact": artifact,
                "model_path": model_path,
                "model_fingerprint_sha256": _model_fingerprint(artifact),
                "scores": scores,
            })
    return contexts


def run_tie_sensitivity(cfg: dict, contexts: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for context in contexts:
        for k_fraction in cfg["k_fractions"]:
            row = boundary_tie_sensitivity(
                context["y_test"],
                context["scores"],
                float(k_fraction),
                context["X_test"]["child_id"].to_numpy(),
            )
            row.update({
                "generator_seed": context["seed"],
                "evaluation": context["evaluation"],
                "model": PRIMARY_MODEL,
                "model_fingerprint_sha256": context["model_fingerprint_sha256"],
            })
            row["recall_range_width"] = row["max_recall_at_k"] - row["min_recall_at_k"]
            row["precision_range_width"] = row["max_precision_at_k"] - row["min_precision_at_k"]
            row["lift_range_width"] = row["max_lift_at_k"] - row["min_lift_at_k"]
            rows.append(row)
    per_seed = pd.DataFrame(rows)
    expected = len(cfg["seeds"]) * len(cfg["splits"]) * len(cfg["k_fractions"])
    keys = ["generator_seed", "evaluation", "k_fraction"]
    if len(per_seed) != expected or per_seed.duplicated(keys).any():
        raise AssertionError(f"Tie audit harus berisi {expected} kombinasi unik.")
    if (
        set(per_seed["generator_seed"]) != set(cfg["seeds"])
        or set(per_seed["evaluation"]) != set(cfg["splits"])
        or set(per_seed["k_fraction"]) != set(cfg["k_fractions"])
    ):
        raise AssertionError("Seed, evaluasi, atau K pada tie audit tidak lengkap.")
    expected_k = [max(1, int(round(n * k))) for n, k in zip(
        per_seed["n_children"], per_seed["k_fraction"]
    )]
    if not np.array_equal(per_seed["k_count"].to_numpy(), expected_k):
        raise AssertionError("Tie audit tidak memakai exact K.")

    summaries = []
    for (evaluation, k_fraction), group in per_seed.groupby(
        ["evaluation", "k_fraction"], sort=False
    ):
        worst = group.sort_values(
            ["recall_range_width", "n_score_equal_cutoff", "generator_seed"],
            ascending=[False, False, True],
        ).iloc[0]
        summaries.append({
            "evaluation": evaluation,
            "k_fraction": k_fraction,
            "n_seeds": len(group),
            "mean_tied_group_size": float(group["n_score_equal_cutoff"].mean()),
            "max_tied_group_size": int(group["n_score_equal_cutoff"].max()),
            "mean_observed_recall_at_k": float(group["observed_recall_at_k"].mean()),
            "mean_min_recall_at_k": float(group["min_recall_at_k"].mean()),
            "mean_max_recall_at_k": float(group["max_recall_at_k"].mean()),
            "mean_recall_range_width": float(group["recall_range_width"].mean()),
            "max_recall_range_width": float(group["recall_range_width"].max()),
            "mean_precision_range_width": float(group["precision_range_width"].mean()),
            "max_precision_range_width": float(group["precision_range_width"].max()),
            "mean_lift_range_width": float(group["lift_range_width"].mean()),
            "max_lift_range_width": float(group["lift_range_width"].max()),
            "worst_seed": int(worst["generator_seed"]),
            "worst_tied_group_size": int(worst["n_score_equal_cutoff"]),
        })
    summary = pd.DataFrame(summaries)
    out = Path(cfg["output_dir"])
    per_seed.to_csv(out / "tab12_tie_sensitivity.csv", index=False)
    summary.to_csv(out / "tab12_tie_sensitivity_summary.csv", index=False)
    return per_seed, summary


def _history_mask(raw: pd.DataFrame, X_test: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    if not X_test["child_id"].is_unique:
        raise AssertionError("Robustness memerlukan satu index visit per anak.")
    cutoffs = X_test.set_index("child_id")["prediction_date"]
    row_cutoff = raw["child_id"].map(cutoffs)
    dates = pd.to_datetime(raw["visit_date"])
    mask = row_cutoff.notna() & dates.le(pd.to_datetime(row_cutoff))
    return mask, row_cutoff


def perturb_raw_history(
    raw: pd.DataFrame,
    X_test: pd.DataFrame,
    *,
    generator_seed: int,
    scenario: str,
    kind: str,
    level: float,
) -> tuple[pd.DataFrame, dict]:
    """Perturb only measurements available no later than each prediction date."""
    perturbed = raw.copy()
    history, row_cutoff = _history_mask(raw, X_test)
    candidates = history & raw["length_cm"].notna()
    changed = pd.Series(False, index=raw.index)
    seed = scenario_seed(generator_seed, scenario)
    rng = np.random.default_rng(seed)

    if kind == "none":
        pass
    elif kind == "length_noise_cm":
        changed = candidates.copy()
        perturbed.loc[changed, "length_cm"] = (
            pd.to_numeric(perturbed.loc[changed, "length_cm"])
            + rng.normal(0.0, level, int(changed.sum()))
        )
    elif kind == "length_missing_fraction":
        candidate_idx = raw.index[candidates].to_numpy()
        n_remove = int(round(level * len(candidate_idx)))
        chosen = rng.choice(candidate_idx, size=n_remove, replace=False)
        changed.loc[chosen] = True
        perturbed.loc[changed, "length_cm"] = np.nan
    elif kind == "current_measurement_missing":
        current = raw.index.isin(X_test.index)
        changed.loc[current] = True
        perturbed.loc[changed, "length_cm"] = np.nan
    else:
        raise ValueError(f"Jenis perturbasi tidak dikenal: {kind!r}")

    if (changed & ~history).any():
        raise AssertionError("Perturbasi menyentuh pengukuran setelah prediction_date.")
    if changed.any():
        perturbed.loc[changed, "haz"] = haz_series(perturbed.loc[changed])
    changed_dates = pd.to_datetime(raw.loc[changed, "visit_date"])
    return perturbed, {
        "perturbation_seed": seed,
        "n_candidate_measurements": int(candidates.sum()),
        "n_perturbed_measurements": int(changed.sum()),
        "realized_perturbation_fraction": (
            float(changed.sum() / candidates.sum()) if candidates.any() else 0.0
        ),
        "max_perturbed_date": (
            changed_dates.max().date().isoformat() if len(changed_dates) else ""
        ),
        "causal_timing_verified": bool(
            (pd.to_datetime(raw.loc[changed, "visit_date"])
             <= pd.to_datetime(row_cutoff.loc[changed])).all()
        ),
    }


def run_robustness(cfg: dict, contexts: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for context in contexts:
        scenario_rows = []
        for scenario, kind, level in SCENARIOS:
            if kind == "none":
                X_scenario = context["X_test"]
                scores = context["scores"]
                _, metadata = perturb_raw_history(
                    context["raw"], context["X_test"],
                    generator_seed=context["seed"], scenario=scenario, kind=kind, level=level,
                )
            else:
                perturbed, metadata = perturb_raw_history(
                    context["raw"], context["X_test"],
                    generator_seed=context["seed"], scenario=scenario, kind=kind, level=level,
                )
                X_scenario = build_dataset(
                    perturbed,
                    ["snapshot", "trajectory"],
                    output_indices=context["X_test"].index,
                )
                scores = predict_artifact(context["artifact"], X_scenario)
            finite = np.isfinite(scores)
            y = context["y_test"].to_numpy()[finite]
            tie = X_scenario["child_id"].to_numpy()[finite]
            metrics = evaluate_ranking(y, scores[finite], tuple(cfg["k_fractions"]), tie)
            row = {
                "generator_seed": context["seed"],
                "evaluation": context["evaluation"],
                "model": PRIMARY_MODEL,
                "model_fingerprint_sha256": context["model_fingerprint_sha256"],
                "scenario": scenario,
                "perturbation_kind": kind,
                "perturbation_level": level,
                "n_intended": len(context["y_test"]),
                "n_scored": int(finite.sum()),
                "coverage": float(finite.mean()),
                **metadata,
                **{metric: metrics[metric] for metric in ROBUSTNESS_METRICS[:10]},
            }
            scenario_rows.append(row)
        baseline = scenario_rows[0]
        for row in scenario_rows:
            row["delta_auprc"] = row["auprc"] - baseline["auprc"]
            for metric in ("recall@20%", "precision@20%", "lift@20%"):
                row[f"delta_{metric}"] = row[metric] - baseline[metric]
        rows.extend(scenario_rows)

    per_seed = pd.DataFrame(rows)
    expected = len(cfg["seeds"]) * len(cfg["splits"]) * len(SCENARIOS)
    if len(per_seed) != expected or per_seed.duplicated(
        ["generator_seed", "evaluation", "scenario"]
    ).any():
        raise AssertionError(f"TAB-08 harus berisi {expected} kombinasi unik.")
    if (
        set(per_seed["generator_seed"]) != set(cfg["seeds"])
        or set(per_seed["evaluation"]) != set(cfg["splits"])
        or set(per_seed["scenario"]) != {scenario for scenario, _, _ in SCENARIOS}
    ):
        raise AssertionError("Seed, evaluasi, atau skenario TAB-08 tidak lengkap.")
    if not per_seed["causal_timing_verified"].all():
        raise AssertionError("Ada perturbasi TAB-08 yang melewati prediction_date.")
    if (per_seed["n_scored"] > per_seed["n_intended"]).any():
        raise AssertionError("n_scored tidak boleh melebihi n_intended.")

    metadata_cols = ["evaluation", "scenario", "perturbation_kind", "perturbation_level"]
    long = per_seed.melt(
        id_vars=metadata_cols + ["generator_seed"],
        value_vars=list(ROBUSTNESS_METRICS),
        var_name="metric",
        value_name="value",
    )
    aggregate = long.groupby(metadata_cols + ["metric"], sort=False)["value"].agg(
        mean="mean", std="std", n_seeds="count"
    ).reset_index()
    aggregate["mean_std"] = [
        f"{mean:.4f} ± {std:.4f}" for mean, std in zip(aggregate["mean"], aggregate["std"])
    ]
    out = Path(cfg["output_dir"])
    per_seed.to_csv(out / "tab08_robustness_per_seed.csv", index=False)
    aggregate.to_csv(out / "tab08_robustness_aggregate.csv", index=False)
    return per_seed, aggregate


def benchmark_batches(
    frame: pd.DataFrame, feature_names: list[str], sizes: tuple[int, ...]
) -> dict[int, pd.DataFrame]:
    missing = set(feature_names) - set(frame.columns)
    if missing:
        raise ValueError(f"Kolom benchmark hilang: {sorted(missing)}")
    if not frame.index.is_unique:
        raise ValueError("Frame benchmark harus berindex unik.")
    ordered = frame.sort_values(["child_id", "prediction_date"])
    if any(size <= 0 or size > len(ordered) for size in sizes):
        raise ValueError("Ukuran batch harus di (0, jumlah baris].")
    return {size: ordered.iloc[:size].copy() for size in sizes}


def _timings(callable_, repetitions: int, warmups: int = 10) -> tuple[float, float]:
    if repetitions < 2:
        raise ValueError("Benchmark memerlukan minimal dua repetisi.")
    for _ in range(warmups):
        callable_()
    samples = np.empty(repetitions, dtype=float)
    for i in range(repetitions):
        start = time.perf_counter_ns()
        callable_()
        samples[i] = (time.perf_counter_ns() - start) / 1_000_000
    return float(np.median(samples)), float(np.percentile(samples, 95))


def _cpu_name() -> str | None:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def run_latency(
    cfg: dict,
    *,
    source_git_commit: str,
    source_git_dirty: bool,
    load_repetitions: int = 100,
    prediction_repetitions: int = 200,
) -> tuple[pd.DataFrame, dict]:
    out = Path(cfg["output_dir"])
    model_path = out / "primary_model.joblib"
    metadata_path = out / "primary_model_metadata.json"
    artifact = load_artifact(model_path)

    fixture = pd.read_csv(out / "persistence_fixture.csv")
    expected = pd.read_csv(out / "persistence_expected_predictions.csv")["prediction"].to_numpy()
    actual = predict_artifact(artifact, fixture)
    max_difference = float(np.max(np.abs(expected - actual)))
    if not np.allclose(expected, actual, rtol=0.0, atol=1e-12):
        raise AssertionError("Fixture persistensi berubah sebelum benchmark.")

    seed = int(cfg["primary_seed"])
    raw = load_dataset(_ensure_cohort(cfg, seed))
    X, _, _ = prepare(raw)
    test_idx = _test_indices(X, cfg["primary_split"], seed)
    frame = X.loc[test_idx]
    full_size = len(frame)
    sizes = tuple(dict.fromkeys((1, 10, 100, full_size)))
    batches = benchmark_batches(frame, artifact["feature_names"], sizes)

    model_bytes = model_path.stat().st_size
    metadata_bytes = metadata_path.stat().st_size if metadata_path.exists() else 0
    rows = [{
        "measurement": "model_artifact_size",
        "batch_size": np.nan,
        "repetitions": np.nan,
        "median_ms": np.nan,
        "p95_ms": np.nan,
        "throughput_rows_per_second": np.nan,
        "size_bytes": model_bytes,
        "size_mib": model_bytes / (1024**2),
        "includes_disk_io": True,
        "required_for_inference": True,
    }, {
        "measurement": "supplementary_metadata_size",
        "batch_size": np.nan,
        "repetitions": np.nan,
        "median_ms": np.nan,
        "p95_ms": np.nan,
        "throughput_rows_per_second": np.nan,
        "size_bytes": metadata_bytes,
        "size_mib": metadata_bytes / (1024**2),
        "includes_disk_io": True,
        "required_for_inference": False,
    }]

    median, p95 = _timings(lambda: load_artifact(model_path), load_repetitions, warmups=5)
    rows.append({
        "measurement": "artifact_load",
        "batch_size": np.nan,
        "repetitions": load_repetitions,
        "median_ms": median,
        "p95_ms": p95,
        "throughput_rows_per_second": np.nan,
        "size_bytes": np.nan,
        "size_mib": np.nan,
        "includes_disk_io": True,
        "required_for_inference": True,
    })

    for size, batch in batches.items():
        median, p95 = _timings(
            lambda batch=batch: predict_artifact(artifact, batch), prediction_repetitions
        )
        rows.append({
            "measurement": "warm_predict",
            "batch_size": size,
            "repetitions": prediction_repetitions,
            "median_ms": median,
            "p95_ms": p95,
            "throughput_rows_per_second": size / (median / 1000),
            "size_bytes": np.nan,
            "size_mib": np.nan,
            "includes_disk_io": False,
            "required_for_inference": True,
        })

    full_batch = batches[full_size]
    tie_break = full_batch["child_id"].to_numpy()

    def score_and_rank():
        scores = predict_artifact(artifact, full_batch)
        selected = capacity_predictions(scores, float(cfg["operating_k"]), tie_break)
        if int(selected.sum()) != max(1, int(round(len(full_batch) * cfg["operating_k"]))):
            raise AssertionError("Benchmark ranking tidak memilih exact K.")

    median, p95 = _timings(score_and_rank, prediction_repetitions)
    rows.append({
        "measurement": "score_and_exact_top20_ranking",
        "batch_size": full_size,
        "repetitions": prediction_repetitions,
        "median_ms": median,
        "p95_ms": p95,
        "throughput_rows_per_second": full_size / (median / 1000),
        "size_bytes": np.nan,
        "size_mib": np.nan,
        "includes_disk_io": False,
        "required_for_inference": True,
    })
    latency = pd.DataFrame(rows)
    latency.to_csv(out / "tab10_latency.csv", index=False)

    environment = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": _cpu_name(),
        "logical_cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "packages": {name: version(name) for name in (
            "numpy", "pandas", "scikit-learn", "lightgbm", "joblib"
        )},
        "git_commit": source_git_commit,
        "git_dirty": source_git_dirty,
        "git_dirty_scope": "source state at command start, before generated outputs",
        "model_path": str(model_path),
        "model_sha256": _sha256(model_path),
        "schema_is_embedded": True,
        "required_inference_artifact_bytes": model_bytes,
        "supplementary_metadata_bytes": metadata_bytes,
        "fixture_predictions": len(expected),
        "fixture_tolerance": 1e-12,
        "fixture_max_absolute_difference": max_difference,
        "timer": "time.perf_counter_ns",
        "interpreter_startup_included": False,
    }
    (out / "tab10_latency_environment.json").write_text(
        json.dumps(environment, indent=2), encoding="utf-8"
    )
    return latency, environment


def _compare_csv(reference: Path, candidate: Path, tolerance: float) -> dict:
    a, b = pd.read_csv(reference), pd.read_csv(candidate)
    result = {
        "file": reference.name,
        "byte_equal": reference.read_bytes() == candidate.read_bytes(),
        "shape_equal": a.shape == b.shape,
        "columns_equal": list(a.columns) == list(b.columns),
        "numeric_equal": False,
        "max_absolute_difference": None,
    }
    if not result["shape_equal"] or not result["columns_equal"]:
        return result
    max_difference = 0.0
    equal = True
    for column in a.columns:
        an = pd.to_numeric(a[column], errors="coerce")
        bn = pd.to_numeric(b[column], errors="coerce")
        numeric = an.notna().sum() + a[column].isna().sum() == len(a)
        numeric &= bn.notna().sum() + b[column].isna().sum() == len(b)
        if numeric:
            if not a[column].isna().equals(b[column].isna()):
                equal = False
                continue
            finite = an.notna() & bn.notna()
            if finite.any():
                av = an[finite].to_numpy(dtype=float)
                bv = bn[finite].to_numpy(dtype=float)
                difference = float(np.max(np.abs(av - bv)))
                max_difference = max(max_difference, difference)
                equal &= bool(np.allclose(av, bv, rtol=0.0, atol=tolerance))
        else:
            equal &= a[column].fillna("<NA>").astype(str).equals(
                b[column].fillna("<NA>").astype(str)
            )
    result["numeric_equal"] = bool(equal)
    result["max_absolute_difference"] = max_difference
    return result


def compare_reproduction(cfg: dict, candidate_dir: Path, tolerance: float = 1e-12) -> dict:
    reference_dir = Path(cfg["output_dir"])
    csv_files = (
        "dataset_summary.csv",
        "per_seed_metrics.csv",
        "aggregate_metrics.csv",
        "ablation_deltas_per_seed.csv",
        "ablation_deltas_aggregate.csv",
        "tab07_case_selection_summary.csv",
        "tab07_error_analysis.csv",
        "tab07_representative_cases.csv",
        "tab09_shap_global.csv",
        "persistence_expected_predictions.csv",
        "persistence_fresh_predictions.csv",
    )
    comparisons = [
        _compare_csv(reference_dir / name, candidate_dir / name, tolerance)
        for name in csv_files
    ]
    who_equal = json.loads((reference_dir / "who_validation.json").read_text()) == json.loads(
        (candidate_dir / "who_validation.json").read_text()
    )
    candidate_environment = json.loads((candidate_dir / "environment.json").read_text())
    if candidate_environment.get("git_dirty") is not False:
        raise AssertionError("Verification run tidak berasal dari worktree bersih.")
    if candidate_environment.get("git_commit") != _git_commit():
        raise AssertionError("Commit verification run tidak sama dengan HEAD saat ini.")
    passed = all(item["numeric_equal"] for item in comparisons) and who_equal
    report = {
        "verified_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reference_directory": str(reference_dir),
        "candidate_directory": str(candidate_dir),
        "clean_source_commit": candidate_environment["git_commit"],
        "clean_source_git_dirty": candidate_environment["git_dirty"],
        "absolute_tolerance": tolerance,
        "comparisons": comparisons,
        "who_validation_json_equal": who_equal,
        "passed": passed,
    }
    if not passed:
        raise AssertionError("Regenerasi clean-worktree tidak cocok dengan hasil committed.")
    (reference_dir / "tab13_reproducibility.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def update_closure_summary(cfg: dict) -> None:
    """Append a deterministic measured-evidence section to the final summary."""
    out = Path(cfg["output_dir"])
    required = (
        "tab08_robustness_aggregate.csv",
        "tab10_latency.csv",
        "tab10_latency_environment.json",
        "tab12_tie_sensitivity_summary.csv",
        "tab13_reproducibility.json",
    )
    if not all((out / name).exists() for name in required):
        return

    tie = pd.read_csv(out / "tab12_tie_sensitivity_summary.csv")
    tie_view = pd.DataFrame({
        "evaluation": tie["evaluation"],
        "K": tie["k_fraction"].map(lambda value: f"{value:.0%}"),
        "mean / max cutoff tie": [
            f"{mean:.1f} / {maximum}" for mean, maximum in zip(
                tie["mean_tied_group_size"], tie["max_tied_group_size"]
            )
        ],
        "mean observed recall": tie["mean_observed_recall_at_k"].map(lambda value: f"{value:.4f}"),
        "mean exact recall bounds": [
            f"{minimum:.4f}–{maximum:.4f}" for minimum, maximum in zip(
                tie["mean_min_recall_at_k"], tie["mean_max_recall_at_k"]
            )
        ],
        "max range width": tie["max_recall_range_width"].map(lambda value: f"{value:.4f}"),
        "worst seed": tie["worst_seed"],
    })

    robust = pd.read_csv(out / "tab08_robustness_aggregate.csv")
    wanted = ["auprc", "delta_auprc", "recall@20%", "delta_recall@20%", "coverage"]
    robust = robust[robust["metric"].isin(wanted)].copy()
    robust["scenario"] = pd.Categorical(
        robust["scenario"], [scenario for scenario, _, _ in SCENARIOS], ordered=True
    )
    robust_view = robust.pivot(
        index=["evaluation", "scenario"], columns="metric", values="mean_std"
    ).reset_index().sort_values(["evaluation", "scenario"])
    robust_view = robust_view.rename(columns={
        "auprc": "AUPRC",
        "delta_auprc": "ΔAUPRC",
        "recall@20%": "Recall@20%",
        "delta_recall@20%": "ΔRecall@20%",
        "coverage": "coverage",
    })

    latency = pd.read_csv(out / "tab10_latency.csv")
    timing = latency[latency["median_ms"].notna()][
        ["measurement", "batch_size", "repetitions", "median_ms", "p95_ms",
         "throughput_rows_per_second"]
    ].copy()
    for column in ("batch_size", "repetitions"):
        timing[column] = timing[column].map(
            lambda value: "" if pd.isna(value) else str(int(value))
        )
    for column in ("median_ms", "p95_ms"):
        timing[column] = timing[column].map(lambda value: f"{value:.4f}")
    timing["throughput_rows_per_second"] = timing["throughput_rows_per_second"].map(
        lambda value: "" if pd.isna(value) else f"{value:.1f}"
    )
    latency_environment = json.loads((out / "tab10_latency_environment.json").read_text())
    reproduction = json.loads((out / "tab13_reproducibility.json").read_text())
    byte_matches = sum(item["byte_equal"] for item in reproduction["comparisons"])

    section = f"""
<!-- TABULAR_CLOSURE_START -->
## TAB-12 — Top-K boundary tie sensitivity

The production rule is unchanged: exact K with deterministic `child_id` tie-breaking.
The ranges below vary only membership inside the cutoff-score tie group.

{_markdown_table(tie_view)}

## TAB-08 — Synthetic input robustness

The frozen M2 model was trained on unperturbed data. Only measurements available by each
prediction date were corrupted; WHO HAZ and dependent features were then recomputed.

{_markdown_table(robust_view)}

`coverage` is the fraction of intended children receiving a finite model score. A valid
manual length remains an observed measurement and is not the same as
`current_measurement_missing`.

## TAB-10 — Current-environment inference benchmark

- Environment: {latency_environment['processor'] or 'processor unavailable'};
  {latency_environment['platform']}; Python {latency_environment['python']}.
- Required model artifact: {latency_environment['required_inference_artifact_bytes']} bytes
  ({latency_environment['required_inference_artifact_bytes'] / (1024**2):.4f} MiB); schema embedded.
- Interpreter startup and CSV I/O are excluded from warm prediction timings.

{_markdown_table(timing)}

## Clean-source reproducibility verification

The committed `TAB-FINAL-01` was regenerated in a detached clean worktree at
`{reproduction['clean_source_commit']}` with `git_dirty=false`. All
{len(reproduction['comparisons'])} compared CSV artifacts were numerically equal within
`{reproduction['absolute_tolerance']}`; {byte_matches}/{len(reproduction['comparisons'])}
were byte-identical. WHO validation JSON also matched exactly.

## Closure limitations

Robustness is sensitivity analysis on synthetic cohorts, not evidence of clinical
robustness. Latency applies only to the recorded machine. Equal-score cutoff groups can
make exact-K membership and Recall@K materially tie-break-sensitive even though list size
and ordering remain deterministic. The frozen schema contains `measured_by_cv_t`; TAB-08
does not equate a valid manual measurement with a missing measurement and makes no claim
that scores are invariant to the source flag.
<!-- TABULAR_CLOSURE_END -->
"""
    summary_path = Path(cfg["summary_path"])
    current = summary_path.read_text(encoding="utf-8")
    marker = "<!-- TABULAR_CLOSURE_START -->"
    if marker in current:
        current = current.split(marker, 1)[0].rstrip()
    summary_path.write_text(current.rstrip() + "\n\n" + section.lstrip(), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--analysis", choices=("tie", "robustness", "latency", "all"), required=True
    )
    parser.add_argument("--load-repetitions", type=int, default=100)
    parser.add_argument("--prediction-repetitions", type=int, default=200)
    parser.add_argument("--verification-dir", type=Path)
    args = parser.parse_args()

    source_git_commit, source_git_dirty = _git_commit(), _git_dirty()
    cfg = load_config(args.config)
    contexts = None
    if args.analysis in {"tie", "robustness", "all"}:
        contexts = load_contexts(cfg)
    if args.analysis in {"tie", "all"}:
        run_tie_sensitivity(cfg, contexts)
    if args.analysis in {"robustness", "all"}:
        run_robustness(cfg, contexts)
    if args.analysis in {"latency", "all"}:
        run_latency(
            cfg,
            source_git_commit=source_git_commit,
            source_git_dirty=source_git_dirty,
            load_repetitions=args.load_repetitions,
            prediction_repetitions=args.prediction_repetitions,
        )
    if args.verification_dir is not None:
        compare_reproduction(cfg, args.verification_dir)
    update_closure_summary(cfg)
    print(f"Closure artifacts: {cfg['output_dir']}")


if __name__ == "__main__":
    main()
