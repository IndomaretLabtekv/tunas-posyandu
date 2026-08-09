"""Canonical multi-seed final tabular experiment for Tunas."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from data.generate_synth import SynthConfig, generate, summarize
from tabular.persist import load_artifact
from tabular.target import attach_labels
from tabular.train import ExperimentConfig, run
from tabular.who_lms import haz, haz_series

MODELS = [
    "B0_haz_only", "B1_haz_slope", "B2_logreg",
    "M1_snapshot", "M2_plus_trajectory", "M3_plus_contextual",
]
KEY_METRICS = ["auprc", "recall@20%", "precision@20%", "lift@20%"]


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "experiment_id", "dataset_version", "n_children", "seeds", "splits",
        "k_fractions", "operating_k", "primary_model", "primary_seed",
        "primary_split", "data_dir", "output_dir", "summary_path",
    }
    missing = required - set(cfg)
    if missing:
        raise ValueError(f"Config final belum lengkap: {sorted(missing)}")
    if not 3 <= len(cfg["seeds"]) <= 5 or len(set(cfg["seeds"])) != len(cfg["seeds"]):
        raise ValueError("Final experiment memerlukan 3-5 seed unik.")
    if set(cfg["splits"]) != {"grouped", "temporal"}:
        raise ValueError("Final experiment wajib memuat split grouped dan temporal.")
    if cfg["primary_model"] != "M2_plus_trajectory":
        raise ValueError("M2_plus_trajectory adalah primary model yang dipra-spesifikasikan.")
    if cfg["primary_seed"] not in cfg["seeds"] or cfg["primary_split"] not in cfg["splits"]:
        raise ValueError("Primary seed/split harus termasuk dalam suite final.")
    if int(cfg["n_children"]) <= 0:
        raise ValueError("n_children harus > 0.")
    return cfg


def _aggregate(raw: pd.DataFrame) -> pd.DataFrame:
    excluded = {
        "generator_seed", "random_seed", "evaluation", "model", "score_type",
        "operating_point", "n", "n_positive", "prevalence", "tp", "fp", "fn", "tn",
        "n_flagged", "threshold", "is_probability",
    }
    numeric = raw.copy()
    metrics = []
    for col in raw.columns:
        if col in excluded:
            continue
        converted = pd.to_numeric(raw[col], errors="coerce")
        if converted.notna().any():
            numeric[col] = converted
            metrics.append(col)
    long = numeric.melt(
        id_vars=["generator_seed", "random_seed", "evaluation", "model"],
        value_vars=metrics, var_name="metric", value_name="value",
    ).dropna(subset=["value"])
    out = long.groupby(["evaluation", "model", "metric"], sort=False)["value"].agg(
        mean="mean", std="std", n_seeds="count"
    ).reset_index()
    out["mean_std"] = [f"{m:.4f} ± {s:.4f}" for m, s in zip(out["mean"], out["std"])]
    return out


def _ablation_deltas(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    comparisons = {
        "M2_minus_M1_trajectory": ("M2_plus_trajectory", "M1_snapshot"),
        "M3_minus_M2_contextual": ("M3_plus_contextual", "M2_plus_trajectory"),
    }
    for metric in KEY_METRICS:
        pivot = raw.pivot(index=["evaluation", "generator_seed"], columns="model", values=metric)
        for name, (hi, lo) in comparisons.items():
            delta = (pivot[hi] - pivot[lo]).rename("value").reset_index()
            delta["comparison"] = name
            delta["metric"] = metric
            rows.append(delta)
    per_seed = pd.concat(rows, ignore_index=True)
    aggregate = per_seed.groupby(["evaluation", "comparison", "metric"])["value"].agg(
        mean="mean", std="std", n_seeds="count"
    ).reset_index()
    aggregate["mean_std"] = [
        f"{m:+.4f} ± {s:.4f}" for m, s in zip(aggregate["mean"], aggregate["std"])
    ]
    return per_seed, aggregate


def _markdown_table(df: pd.DataFrame) -> str:
    shown = df.fillna("").astype(str)
    header = "| " + " | ".join(shown.columns) + " |"
    rule = "| " + " | ".join(["---"] * len(shown.columns)) + " |"
    rows = ["| " + " | ".join(row) + " |" for row in shown.to_numpy()]
    return "\n".join([header, rule, *rows])


def _comparison_table(aggregate: pd.DataFrame, evaluation: str) -> pd.DataFrame:
    sub = aggregate[
        (aggregate["evaluation"] == evaluation)
        & aggregate["metric"].isin(KEY_METRICS)
    ]
    table = sub.pivot(index="model", columns="metric", values="mean_std").reindex(MODELS)
    return table.reset_index().rename(columns={"model": "Model"})


def _git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _git_dirty() -> bool:
    return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())


def validate_outputs(cfg: dict, raw: pd.DataFrame, aggregate: pd.DataFrame, out_dir: Path) -> None:
    """Fail closed bila suite final atau artefak audit tidak lengkap."""
    expected_rows = len(cfg["seeds"]) * len(cfg["splits"]) * len(MODELS)
    keys = ["generator_seed", "evaluation", "model"]
    if len(raw) != expected_rows or raw.duplicated(keys).any():
        raise AssertionError(f"Per-seed metrics harus berisi {expected_rows} kombinasi unik.")
    if set(raw["model"]) != set(MODELS) or set(raw["evaluation"]) != set(cfg["splits"]):
        raise AssertionError("Model atau protokol evaluasi final tidak lengkap.")
    if not aggregate["n_seeds"].eq(len(cfg["seeds"])).all():
        raise AssertionError("Ada metrik agregat yang tidak mencakup seluruh seed.")

    expected_k = raw["n"].astype(int).map(
        lambda n: max(1, int(round(float(cfg["operating_k"]) * n)))
    )
    if not raw["n_flagged"].astype(int).eq(expected_k).all():
        raise AssertionError("Daftar kapasitas tidak memilih tepat K anak.")

    cases = pd.read_csv(out_dir / "tab07_representative_cases.csv")
    case_summary = pd.read_csv(out_dir / "tab07_case_selection_summary.csv")
    required_cases = {
        "high_priority_false_positive", "missed_positive", "capacity_boundary",
        "trajectory_rank_change", "short_or_sparse_history",
    }
    if set(case_summary["case_type"]) != required_cases:
        raise AssertionError("Ringkasan kategori kasus error tidak lengkap.")
    available = case_summary[case_summary["candidate_count"] > 0]
    if (available["selected_count"] <= 0).any():
        raise AssertionError("Kategori kasus yang tersedia tidak punya contoh representatif.")

    artifact = load_artifact(out_dir / "primary_model.joblib")
    shap_cases = pd.read_csv(out_dir / "tab09_shap_representative_cases.csv")
    if not set(shap_cases["feature"]).issubset(set(artifact["feature_names"])):
        raise AssertionError("Nama fitur SHAP tidak cocok dengan artefak model.")
    shown = pd.to_numeric(shap_cases["shap_value"])
    expected_direction = np.where(shown == 0, "netral", np.where(shown > 0, "menaikkan", "menurunkan"))
    if not np.array_equal(shap_cases["direction"].to_numpy(), expected_direction):
        raise AssertionError("Arah SHAP tidak cocok dengan nilai yang ditampilkan.")

    persistence = json.loads((out_dir / "persistence_check.json").read_text(encoding="utf-8"))
    if not persistence.get("passed"):
        raise AssertionError("Fresh-process persistence check belum lulus.")


def _write_summary(
    path: Path, cfg: dict, environment: dict, datasets: pd.DataFrame,
    aggregate: pd.DataFrame, delta_aggregate: pd.DataFrame, out_dir: Path,
    who_result: dict,
) -> None:
    dataset_view = datasets[[
        "seed", "n_children", "n_visits", "eligible_rows", "target_prevalence"
    ]].copy()
    dataset_view["target_prevalence"] = dataset_view["target_prevalence"].map(lambda x: f"{x:.4f}")

    delta_view = delta_aggregate[
        delta_aggregate["metric"].isin(["auprc", "recall@20%"])
    ][["evaluation", "comparison", "metric", "mean_std"]]
    errors = pd.read_csv(out_dir / "tab07_error_analysis.csv")[["group", "n"]]
    case_selection = pd.read_csv(out_dir / "tab07_case_selection_summary.csv")
    shap_top = pd.read_csv(out_dir / "tab09_shap_global.csv").head(5)[
        ["feature", "mean_abs_shap"]
    ]

    text = f"""# Final Tabular Experiment Results

## Environment

- Python: {environment['python']}
- Git commit: `{environment['git_commit']}`
- Git working tree dirty during run: `{str(environment['git_dirty']).lower()}`
- Packages: {', '.join(f'{k} {v}' for k, v in environment['packages'].items())}
- Config: `{cfg['experiment_id']}`

## WHO validation

- Official source: WHO Child Growth Standards `lenanthro.sas7bdat` from the official SAS macro package.
- Scope: recumbent length-for-age, female/male, ages 0–730 days.
- Independent checks: {who_result['n_cases']} cases from separate WHO simplified field tables.
- Result: all passed; maximum absolute HAZ difference {who_result['max_abs_error']:.4f} (tolerance 0.05 for 0.1 cm rounded reference lengths).

## Dataset

- Generator: `{cfg['dataset_version']}`, {cfg['n_children']} requested children per seed.
- Seeds: {', '.join(map(str, cfg['seeds']))}.
- The target is prospective deterioration at 91 ± 42 days, not current stunting status.

{_markdown_table(dataset_view)}

## Evaluation

One index visit per child is ranked globally. Exact-K selection uses `child_id` as a deterministic tie-break. Values are mean ± sample standard deviation over {len(cfg['seeds'])} seeds.

### Grouped child holdout

{_markdown_table(_comparison_table(aggregate, 'grouped'))}

### Temporal holdout with label-maturity purge

{_markdown_table(_comparison_table(aggregate, 'temporal'))}

## Primary model

`M2_plus_trajectory` was pre-specified as primary and remains primary regardless of which model has the best final test metric. The persisted artifact is `results/tabular/final/primary_model.joblib`.

## Robustness and ablation

{_markdown_table(delta_view)}

Positive `M2_minus_M1_trajectory` values mean trajectory features add ranking signal over the snapshot model within this controlled synthetic environment. They do not establish clinical effectiveness.

## Error analysis

{_markdown_table(errors)}

Representative cases are selected by deterministic rules in `tab07_representative_cases.csv`. A zero candidate count means that category did not occur in the primary grouped test set.

{_markdown_table(case_selection)}

Top global M2 feature attributions (raw-model log-odds SHAP; non-causal):

{_markdown_table(shap_top)}

## Limitations

Performance on these synthetic cohorts validates pipeline and mechanism behavior only. It is not external clinical validation, does not demonstrate benefit on real children, and is not evidence that Tunas improves real-world child-health outcomes. The generator is a simplified world model, and the operational deterioration threshold has not been clinically validated.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_final(config_path: Path) -> dict:
    cfg = load_config(config_path)
    out_dir, data_dir = Path(cfg["output_dir"]), Path(cfg["data_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_rows, rule_rows, dataset_rows = [], [], []
    primary = None

    for seed in cfg["seeds"]:
        synth_cfg = SynthConfig(n_children=int(cfg["n_children"]), seed=int(seed))
        cohort = generate(synth_cfg)
        cohort["haz"] = haz_series(cohort)
        data_path = data_dir / f"{cfg['dataset_version']}_seed_{seed}.csv"
        cohort.to_csv(data_path, index=False)
        data_path.with_suffix(".config.json").write_text(
            json.dumps(asdict(synth_cfg), indent=2), encoding="utf-8"
        )

        stats = summarize(cohort)["value"].to_dict()
        labels = attach_labels(cohort)["y_deterioration"].dropna()
        dataset_rows.append({
            "seed": seed,
            "n_children": int(stats["n_children"]),
            "n_visits": int(stats["n_visits"]),
            "eligible_rows": int(len(labels)),
            "target_prevalence": float(labels.mean()),
            "missing_length_pct": float(stats["missing_length_pct"]),
            "missing_weight_pct": float(stats["missing_weight_pct"]),
        })

        for split_kind in cfg["splits"]:
            run_dir = out_dir / "runs" / f"seed_{seed}" / split_kind
            result = run(ExperimentConfig(
                data_path=data_path,
                out_dir=run_dir,
                seed=int(seed),
                split_kind=split_kind,
                k_fractions=tuple(cfg["k_fractions"]),
                operating_k=float(cfg["operating_k"]),
                primary_model=cfg["primary_model"],
            ))
            table = result["table"].copy()
            table.insert(0, "evaluation", split_kind)
            table.insert(0, "random_seed", seed)
            table.insert(0, "generator_seed", seed)
            raw_rows.append(table)

            rules = result["rule_table"].copy()
            rules.insert(0, "evaluation", split_kind)
            rules.insert(0, "random_seed", seed)
            rules.insert(0, "generator_seed", seed)
            rule_rows.append(rules)

            if seed == cfg["primary_seed"] and split_kind == cfg["primary_split"]:
                primary = (result, run_dir)

    raw = pd.concat(raw_rows, ignore_index=True)
    raw.to_csv(out_dir / "per_seed_metrics.csv", index=False)
    pd.concat(rule_rows, ignore_index=True).to_csv(out_dir / "rule_metrics.csv", index=False)
    datasets = pd.DataFrame(dataset_rows)
    datasets.to_csv(out_dir / "dataset_summary.csv", index=False)

    aggregate = _aggregate(raw)
    aggregate.to_csv(out_dir / "aggregate_metrics.csv", index=False)
    raw[raw["evaluation"] == "grouped"].to_csv(out_dir / "grouped_metrics.csv", index=False)
    raw[raw["evaluation"] == "temporal"].to_csv(out_dir / "temporal_metrics.csv", index=False)
    aggregate[aggregate["metric"].str.contains("@", regex=False)].to_csv(
        out_dir / "capacity_metrics.csv", index=False
    )
    aggregate[aggregate["metric"].isin(KEY_METRICS)].to_csv(
        out_dir / "baseline_model_comparison.csv", index=False
    )
    aggregate[aggregate["model"].isin(["M1_snapshot", "M2_plus_trajectory", "M3_plus_contextual"])].to_csv(
        out_dir / "ablation_metrics.csv", index=False
    )
    delta_raw, delta_aggregate = _ablation_deltas(raw)
    delta_raw.to_csv(out_dir / "ablation_deltas_per_seed.csv", index=False)
    delta_aggregate.to_csv(out_dir / "ablation_deltas_aggregate.csv", index=False)

    if primary is None:  # guarded by config validation; keeps failures explicit
        raise RuntimeError("Primary run tidak ditemukan.")
    primary_result, primary_run_dir = primary
    copy_names = [
        "primary_model.joblib", "tab04_manifest.json", "tab07_error_analysis.csv",
        "tab07_representative_cases.csv", "tab07_case_selection_summary.csv",
        "tab09_shap_global.csv",
        "tab09_shap_representative_cases.csv", "tab09_shap_top_children.csv",
        "tab11_slice_report.csv",
    ]
    for name in copy_names:
        shutil.copy2(primary_run_dir / name, out_dir / name)

    # Fresh-process persistence verification on a fixed, committed fixture.
    fixture = primary_result["X_test"].sort_values(["child_id", "prediction_date"])[
        primary_result["primary_cols"]
    ].head(8)
    fixture_path = out_dir / "persistence_fixture.csv"
    fresh_path = out_dir / "persistence_fresh_predictions.csv"
    expected_path = out_dir / "persistence_expected_predictions.csv"
    fixture.to_csv(fixture_path, index=False)
    fixture_reloaded = pd.read_csv(fixture_path)
    expected = primary_result["primary_model"].predict_proba(
        fixture_reloaded[primary_result["primary_cols"]]
    )[:, 1]
    pd.DataFrame({"prediction": expected}).to_csv(expected_path, index=False)
    command = [
        sys.executable, "-m", "tabular.persist", "--model", str(out_dir / "primary_model.joblib"),
        "--input", str(fixture_path), "--output", str(fresh_path),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    fresh = pd.read_csv(fresh_path)["prediction"].to_numpy()
    max_diff = float(np.max(np.abs(expected - fresh)))
    tolerance = 1e-12
    if not np.allclose(expected, fresh, rtol=0.0, atol=tolerance):
        raise AssertionError(f"Prediksi model berubah setelah reload: max diff {max_diff}")
    persistence = {
        "passed": True, "n_predictions": len(expected),
        "absolute_tolerance": tolerance, "max_absolute_difference": max_diff,
        "fresh_process_command": "python -m tabular.persist --model results/tabular/final/primary_model.joblib --input results/tabular/final/persistence_fixture.csv --output results/tabular/final/persistence_fresh_predictions.csv",
    }
    (out_dir / "persistence_check.json").write_text(json.dumps(persistence, indent=2), encoding="utf-8")

    artifact = load_artifact(out_dir / "primary_model.joblib")
    primary_metadata = dict(artifact["metadata"])
    primary_metadata.update({
        "artifact_version": artifact["artifact_version"],
        "artifact_path": str(out_dir / "primary_model.joblib"),
        "feature_names": artifact["feature_names"],
        "persistence_check": persistence,
    })
    (out_dir / "primary_model_metadata.json").write_text(
        json.dumps(primary_metadata, indent=2), encoding="utf-8"
    )

    environment = {
        "python": platform.python_version(),
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "packages": {name: version(name) for name in (
            "numpy", "pandas", "scikit-learn", "lightgbm", "shap", "joblib"
        )},
        "config": str(config_path),
    }
    (out_dir / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")

    provenance = json.loads(Path("data/who/provenance.json").read_text(encoding="utf-8"))
    cases = pd.read_csv("tests/who_reference_cases.csv")
    errors = [abs(haz(r.length_cm, r.sex, r.age_days) - r.expected_haz) for r in cases.itertuples()]
    who_result = {
        "source": provenance["sources"][0]["url"],
        "n_cases": len(cases),
        "max_abs_error": max(errors),
    }
    (out_dir / "who_validation.json").write_text(json.dumps(who_result, indent=2), encoding="utf-8")

    validate_outputs(cfg, raw, aggregate, out_dir)
    _write_summary(
        Path(cfg["summary_path"]), cfg, environment, datasets, aggregate,
        delta_aggregate, out_dir, who_result,
    )
    return {
        "raw": raw, "aggregate": aggregate, "datasets": datasets,
        "persistence": persistence, "output_dir": out_dir,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    result = run_final(args.config)
    print(_comparison_table(result["aggregate"], "grouped").to_string(index=False))
    print(f"\nArtifacts: {result['output_dir']}")


if __name__ == "__main__":
    main()
