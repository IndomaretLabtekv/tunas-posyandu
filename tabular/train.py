"""Orkestrasi eksperimen model prioritisasi (TAB-04, TAB-05).

Menjalankan seluruh pembanding pada **target dan split yang identik** lalu
menghasilkan tabel utama paper 4.2:

    B0    ranking -HAZ_t                       proxy baseline HAZ terkini
    B1    ranking HAZ + slope                  bobot dari validation split
    B2    logistic regression (snapshot)
    M1    LightGBM snapshot
    M2    LightGBM snapshot + trajectory       <- ablasi kunci
    M3    LightGBM snapshot + trajectory + contextual
    RULE  aturan biner HAZ_t < -2              hanya metrik klasifikasi

Selisih M2 terhadap M1 mengukur nilai tambah prediktif fitur lintasan pada
kohort sintetis -- ini bukan bukti kebaruan (kebaruan dibuktikan lewat kajian
literatur), melainkan bukti bahwa fitur tersebut berkontribusi.
Selisih M2/M3 terhadap B0 adalah narasi *before -> after* yang terkuantifikasi.
Kalau selisihnya kecil, laporkan apa adanya -- pembahasan trade-off yang jujur
bernilai lebih tinggi daripada klaim tanpa dukungan angka.

Seluruh keluaran ditulis ke `results/tabular/` beserta manifest berisi seed,
commit, ukuran split, dan daftar `child_id` per split, agar setiap angka di
paper dapat ditelusuri kembali (DEC-003).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from tabular.baselines import b0_haz_only, fit_b1, make_b2, rule_stunted_now
from tabular.evaluate import (
    capacity_predictions,
    compare_models,
    error_analysis,
    evaluate_all,
    slice_report,
)
from tabular.features import build_dataset, feature_columns
from tabular.persist import load_artifact, save_artifact
from tabular.splits import (
    assert_features_not_future,
    assert_no_child_leakage,
    grouped_split,
    temporal_split,
)
from tabular.target import (
    HAZ_DROP_THRESHOLD,
    HORIZON_DAYS,
    STUNTING_THRESHOLD,
    WINDOW_TOLERANCE_DAYS,
    attach_labels,
    drop_report,
)

LGB_PARAMS = {
    "objective": "binary",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 40,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "reg_lambda": 1.0,
    "n_estimators": 600,
    "verbose": -1,
}


@dataclass
class ExperimentConfig:
    data_path: Path = Path("data/synth/posyandu_synth_v1.csv")
    out_dir: Path = Path("results/tabular")
    seed: int = 42
    split_kind: str = "grouped"          # "grouped" | "temporal"
    k_fractions: tuple = (0.05, 0.10, 0.20)
    early_stopping_rounds: int = 50
    operating_k: float = 0.20
    # Model utama DITETAPKAN DI MUKA, bukan dipilih dari test set. M2 adalah
    # kontribusi inti paper (snapshot + lintasan); M3 adalah eksperimen
    # tambahan blok kontekstual. Memilih "yang terbaik" berdasarkan test
    # adalah bentuk kebocoran lain.
    primary_model: str = "M2_plus_trajectory"
    selection_rule: str = "pre-specified trajectory model (bukan dipilih dari test)"
    # Unit evaluasi. Klaim produk berbunyi "K% dari ANAK yang dipantau", jadi
    # daftar prioritas harus satu baris per anak. Melatih tetap memakai seluruh
    # kunjungan (lebih banyak data); yang dibatasi hanya evaluasi.
    evaluation_unit: str = "one_index_visit_per_child"
    # Validation memakai unit yang SAMA dengan evaluasi. Kalau tuning memakai
    # seluruh kunjungan sementara penilaian akhir per anak, objektif keduanya
    # berbeda: anak yang lebih sering datang berbobot 10-20 kali saat memilih
    # bobot B1 dan `best_iteration`, padahal di test berbobot satu. Dengan
    # attendance MNAR pada generator, ini dapat menggeser perbandingan M1/M2/M3.
    validation_unit: str = "one_latest_eligible_visit_per_child"
    slice_columns: list = field(default_factory=lambda: ["sex_is_male", "age_bin", "history_bin"])


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    try:
        return bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip())
    except Exception:
        return True


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["visit_date"])
    if "haz" not in df.columns:
        raise ValueError(
            f"{path} tidak memuat kolom `haz`. Jalankan `python -m data.generate_synth` "
            "setelah tabel WHO tersedia."
        )
    return df


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Bangun fitur + label, buang baris tanpa label, kembalikan juga drop report."""
    X = build_dataset(df)
    assert_features_not_future(X)

    labeled = attach_labels(df)
    report = drop_report(labeled)
    y = labeled["y_deterioration"]

    keep = y.notna()
    X = X[keep].copy()
    # Dibawa serta untuk temporal split: kapan label baris ini baru diketahui.
    X["label_available_date"] = labeled.loc[keep, "label_available_date"]
    return X, y[keep].astype(int), report


def select_index_visits(X: pd.DataFrame, split_kind: str) -> pd.Index:
    """Satu kunjungan indeks per anak untuk evaluasi.

    Tanpa ini, "top 20%" berarti 20% *kunjungan*, bukan 20% anak: satu anak bisa
    muncul berkali-kali dalam daftar prioritas dan denominatornya bukan jumlah
    anak. Aturan dipilih di muka, bukan berdasarkan skor model:

        grouped   -> kunjungan eligible TERAKHIR per anak (kondisi terkini)
        temporal  -> kunjungan eligible PERTAMA setelah cutoff (prediksi paling
                     awal yang dapat dibuat pada periode uji)
    """
    ordered = X.sort_values(["child_id", "prediction_date"])
    g = ordered.groupby("child_id", sort=False)
    picked = g.tail(1) if split_kind == "grouped" else g.head(1)
    idx = picked.index
    assert X.loc[idx, "child_id"].is_unique, "unit evaluasi harus satu baris per anak"
    return idx


def deterministic_ranks(scores, tie_break) -> np.ndarray:
    """Peringkat 1..N dengan tie-break identik dengan pemilihan kapasitas."""
    scores = np.asarray(scores, dtype=float)
    tie = np.asarray(tie_break).astype(str)
    if len(scores) != len(tie) or not np.isfinite(scores).all():
        raise ValueError("Skor dan tie-break harus sama panjang serta finite.")
    order = np.lexsort((tie, -scores))
    ranks = np.empty(len(scores), dtype=int)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks


def representative_error_cases(
    y_true, primary_scores, snapshot_scores, X: pd.DataFrame, *,
    k_frac: float, n_examples: int = 3,
) -> pd.DataFrame:
    """Pilih kasus audit dengan aturan deterministik, bukan contoh yang dipoles."""
    y = np.asarray(y_true, dtype=int)
    primary_scores = np.asarray(primary_scores, dtype=float)
    snapshot_scores = np.asarray(snapshot_scores, dtype=float)
    tie = X["child_id"].astype(str).to_numpy()
    selected = capacity_predictions(primary_scores, k_frac, tie).astype(bool)
    rank = deterministic_ranks(primary_scores, tie)
    snapshot_rank = deterministic_ranks(snapshot_scores, tie)

    frame = pd.DataFrame({
        "row_index": X.index,
        "child_id": tie,
        "prediction_date": X["prediction_date"].to_numpy(),
        "outcome_label": y,
        "primary_score": primary_scores,
        "primary_rank": rank,
        "selected_at_capacity": selected,
        "snapshot_score": snapshot_scores,
        "snapshot_rank": snapshot_rank,
        # Positif = fitur trajectory menaikkan posisi relatif terhadap M1.
        "trajectory_rank_gain": snapshot_rank - rank,
    }, index=X.index)
    for col in (
        "haz_t", "age_days", "n_prior_visits", "haz_slope_per_month",
        "haz_delta_1visit", "haz_delta_3months", "n_consecutive_declines",
        "ever_stunted_to_date", "visit_gap_days_t", "haz_missing_t",
    ):
        frame[col] = X[col]
    frame["latest_haz"] = frame["haz_t"]

    rows = []

    def take(mask, case_type: str, rule: str, sort_cols, ascending=True, limit=n_examples):
        picked = frame.loc[mask].sort_values(
            list(sort_cols) + ["child_id"], ascending=([ascending] * len(sort_cols)) + [True]
        ).head(limit).copy()
        picked.insert(0, "selection_rule", rule)
        picked.insert(0, "case_type", case_type)
        rows.append(picked)

    take(selected & (y == 0), "high_priority_false_positive",
         "selected negatives with smallest primary rank", ["primary_rank"])
    take((~selected) & (y == 1), "missed_positive",
         "unselected positives nearest the capacity boundary", ["primary_rank"])

    k = int(selected.sum())
    boundary = (rank >= max(1, k - 1)) & (rank <= min(len(rank), k + 2))
    take(boundary, "capacity_boundary", "ranks K-1 through K+2", ["primary_rank"], limit=4)

    changed = frame["trajectory_rank_gain"].abs()
    frame["_abs_rank_change"] = changed
    take(changed > 0, "trajectory_rank_change",
         "largest absolute rank change versus M1 snapshot", ["_abs_rank_change"], ascending=False)

    sparse = pd.to_numeric(frame["n_prior_visits"], errors="coerce") <= 2
    take(sparse, "short_or_sparse_history",
         "highest-ranked cases with at most two prior visits", ["primary_rank"])

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return out.drop(columns="_abs_rank_change", errors="ignore")


def _history_json(df: pd.DataFrame, child_id: str, prediction_date) -> str:
    cols = [c for c in ("visit_date", "age_days", "length_cm", "weight_kg", "haz") if c in df]
    dates = pd.to_datetime(df["visit_date"])
    history = df.loc[
        (df["child_id"].astype(str) == str(child_id)) & (dates <= pd.Timestamp(prediction_date)),
        cols,
    ].sort_values("visit_date")
    return history.to_json(orient="records", date_format="iso")


def _package_versions() -> dict:
    return {name: version(name) for name in (
        "numpy", "pandas", "scikit-learn", "lightgbm", "shap", "joblib"
    )}


def _fit_lgb(X_tr, y_tr, X_val, y_val, cols, cfg: ExperimentConfig):
    import lightgbm as lgb

    # scale_pos_weight menangani ketidakseimbangan kelas tanpa membuang data
    # mayoritas -- membuang baris justru menghilangkan informasi lintasan.
    pos = max(int(y_tr.sum()), 1)
    neg = max(len(y_tr) - pos, 1)
    model = lgb.LGBMClassifier(**LGB_PARAMS, random_state=cfg.seed, scale_pos_weight=neg / pos)
    model.fit(
        X_tr[cols], y_tr,
        eval_set=[(X_val[cols], y_val)],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(cfg.early_stopping_rounds, verbose=False)],
    )
    return model


def run(cfg: ExperimentConfig) -> dict:
    df = load_dataset(cfg.data_path)
    X, y, drops = prepare(df)

    if cfg.split_kind == "grouped":
        split = grouped_split(X, seed=cfg.seed)
        assert_no_child_leakage(split)
    elif cfg.split_kind == "temporal":
        split = temporal_split(
            X, date_col="prediction_date", seed=cfg.seed,
            label_available_col="label_available_date",
        )
    else:
        raise ValueError(f"split_kind tidak dikenal: {cfg.split_kind!r}")

    tr, va_all, te_all = split.train, split.val, split.test

    # Pelatihan memakai SELURUH kunjungan (lebih banyak data).
    # Validation & test memakai satu kunjungan indeks per anak.
    #
    # Validation selalu memakai aturan "kunjungan eligible terakhir": pada run
    # temporal, validation berasal dari pool pra-cutoff, sehingga kunjungan
    # terakhir adalah yang paling dekat ke cutoff dan berhistori paling lengkap.
    va = select_index_visits(X.loc[va_all], "grouped")
    te = select_index_visits(X.loc[te_all], cfg.split_kind)

    X_tr, X_va, X_te = X.loc[tr], X.loc[va], X.loc[te]
    y_tr, y_va, y_te = y.loc[tr], y.loc[va], y.loc[te]

    snap = feature_columns(["snapshot"])
    snap_traj = feature_columns(["snapshot", "trajectory"])
    full = feature_columns(["snapshot", "trajectory", "contextual"])

    scores: dict[str, np.ndarray] = {}
    score_types: dict[str, str] = {}

    # --- baseline
    scores["B0_haz_only"] = b0_haz_only(X_te);              score_types["B0_haz_only"] = "ranking"
    # preprocessing dari TRAIN, bobot dari VALIDATION, test hanya predict
    b1 = fit_b1(X_tr, X_va, y_va, k_frac=cfg.operating_k)
    scores["B1_haz_slope"] = b1.predict(X_te);              score_types["B1_haz_slope"] = "ranking"
    b2 = make_b2(seed=cfg.seed).fit(X_tr[snap], y_tr)
    scores["B2_logreg"] = b2.predict_proba(X_te[snap])[:, 1]; score_types["B2_logreg"] = "probability"

    # --- LightGBM + ablasi blok fitur
    models = {}
    for name, cols in (("M1_snapshot", snap), ("M2_plus_trajectory", snap_traj), ("M3_plus_contextual", full)):
        m = _fit_lgb(X_tr, y_tr, X_va, y_va, cols, cfg)
        models[name] = (m, cols)
        scores[name] = m.predict_proba(X_te[cols])[:, 1]
        score_types[name] = "probability"

    # Titik operasi seragam = skenario kapasitas tindak lanjut, bukan ambang 0.5.
    # Tie-break memakai child_id agar daftar prioritas reprodusibel.
    tie = X_te["child_id"].to_numpy()
    results = {
        n: evaluate_all(y_te, s, score_type=score_types[n], operating_k=cfg.operating_k,
                        tie_break=tie, k_fractions=cfg.k_fractions)
        for n, s in scores.items()
    }
    table = compare_models(results)

    # RULE dilaporkan TERPISAH: skornya biner sehingga tidak dapat mengurutkan
    # anak dalam kelompok yang sama; AUPRC dan metrik @K tidak bermakna baginya.
    rule_result = {
        "RULE_haz_lt_-2": evaluate_all(
            y_te, rule_stunted_now(X_te), score_type="binary_rule", k_fractions=cfg.k_fractions
        )
    }
    rule_table = compare_models(rule_result)

    # --- artefak
    cfg.out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(cfg.out_dir / "tab04_ranking_comparison.csv", index=False)
    rule_table.to_csv(cfg.out_dir / "tab04_rule_comparison.csv", index=False)
    drops.to_csv(cfg.out_dir / "tab04_label_drop_report.csv", index=False)

    if cfg.primary_model not in models:
        raise ValueError(f"primary_model {cfg.primary_model!r} tidak ada di daftar model.")
    primary_model, primary_cols = models[cfg.primary_model]
    primary_scores = scores[cfg.primary_model]
    timestamp_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Satu daftar prioritas global dipakai oleh error analysis DAN slice report,
    # sehingga keduanya menggambarkan keputusan yang sama dengan produk.
    selected = capacity_predictions(primary_scores, cfg.operating_k, tie)

    error_analysis(y_te, primary_scores, X_te[primary_cols],
                   k_frac=cfg.operating_k, tie_break=tie).to_csv(
        cfg.out_dir / "tab07_error_analysis.csv", index=False
    )

    cases = representative_error_cases(
        y_te, primary_scores, scores["M1_snapshot"], X_te,
        k_frac=cfg.operating_k,
    )
    cases["history_json"] = [
        _history_json(df, row.child_id, row.prediction_date)
        for row in cases.itertuples()
    ]
    cases.to_csv(cfg.out_dir / "tab07_representative_cases.csv", index=False)
    primary_rank = deterministic_ranks(primary_scores, tie)
    snapshot_rank = deterministic_ranks(scores["M1_snapshot"], tie)
    y_array = y_te.to_numpy()
    k = int(selected.sum())
    candidate_counts = {
        "high_priority_false_positive": int((selected.astype(bool) & (y_array == 0)).sum()),
        "missed_positive": int((~selected.astype(bool) & (y_array == 1)).sum()),
        "capacity_boundary": int(((primary_rank >= max(1, k - 1))
                                   & (primary_rank <= min(len(primary_rank), k + 2))).sum()),
        "trajectory_rank_change": int((primary_rank != snapshot_rank).sum()),
        "short_or_sparse_history": int((X_te["n_prior_visits"] <= 2).sum()),
    }
    selected_counts = cases["case_type"].value_counts().to_dict()
    pd.DataFrame([
        {"case_type": name, "candidate_count": count,
         "selected_count": int(selected_counts.get(name, 0))}
        for name, count in candidate_counts.items()
    ]).to_csv(cfg.out_dir / "tab07_case_selection_summary.csv", index=False)

    slices = pd.DataFrame({
        "sex_is_male": X_te["sex_is_male"].map({1.0: "M", 0.0: "F"}),
        # include_lowest agar bayi berusia tepat 0 hari tidak jatuh ke luar bin
        # dan hilang dari slice report.
        "age_bin": pd.cut(X_te["age_days"], [0, 180, 365, 548, 731],
                          labels=["0-6bln", "6-12bln", "12-18bln", "18-24bln"],
                          include_lowest=True),
        "history_bin": pd.cut(X_te["n_prior_visits"], [-0.1, 0, 2, 5, 100],
                              labels=["0", "1-2", "3-5", "6+"]),
    })
    slice_report(y_te, primary_scores, slices, selected=selected).to_csv(
        cfg.out_dir / "tab11_slice_report.csv", index=False
    )

    ablation = table[table["model"].isin(["B0_haz_only", "M1_snapshot",
                                          "M2_plus_trajectory", "M3_plus_contextual"])]
    ablation.to_csv(cfg.out_dir / "tab05_ablation.csv", index=False)

    # Persistensi model utama. Tanpa ini, API tidak dapat memuat model dan
    # memanggil Explainer pada anak baru -- eksperimen selesai tetapi produk
    # belum bisa memakainya.
    model_path = cfg.out_dir / "primary_model.joblib"
    data_config_path = cfg.data_path.with_suffix(".config.json")
    data_config = (
        json.loads(data_config_path.read_text(encoding="utf-8"))
        if data_config_path.exists() else {}
    )
    artifact_metadata = {
        "model_name": cfg.primary_model,
        "model_version": "tunas-tabular-m2-v1",
        "created_utc": timestamp_utc,
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "feature_schema": [{"name": c, "dtype": str(X_tr[c].dtype)} for c in primary_cols],
        "training_config": {
            "split_kind": split.kind,
            "operating_k": cfg.operating_k,
            "early_stopping_rounds": cfg.early_stopping_rounds,
            "lgb_params": LGB_PARAMS,
            "selection_rule": cfg.selection_rule,
        },
        "seeds": {"model_and_split": cfg.seed, "generator": data_config.get("seed")},
        "target": {
            "name": "prospective_growth_deterioration",
            "horizon_days": HORIZON_DAYS,
            "window_tolerance_days": WINDOW_TOLERANCE_DAYS,
            "haz_drop_threshold": HAZ_DROP_THRESHOLD,
            "stunting_crossing_threshold": STUNTING_THRESHOLD,
        },
        "data": {"path": str(cfg.data_path), "generator_config": data_config},
        "environment": {"python": sys.version.split()[0], "packages": _package_versions()},
    }
    save_artifact(model_path, primary_model, primary_cols, artifact_metadata)

    # TAB-09 memakai model yang SUDAH dimuat ulang dari artefak, sehingga
    # penjelasan tidak mungkin berasal dari objek in-memory yang berbeda.
    from tabular.explain import Explainer
    persisted = load_artifact(model_path)
    ex = Explainer(persisted["model"], persisted["feature_names"])
    ex.global_importance(X_te[primary_cols]).to_csv(
        cfg.out_dir / "tab09_shap_global.csv", index=False
    )
    top_order = np.lexsort((X_te["child_id"].astype(str).to_numpy(), -primary_scores))[:10]
    top_idx = X_te.index[top_order]
    expl = ex.explain_batch(X_te.loc[top_idx, primary_cols], top_k=5)

    score_by_index = pd.Series(primary_scores, index=X_te.index)
    rank_by_index = pd.Series(deterministic_ranks(primary_scores, tie), index=X_te.index)
    expl.insert(1, "child_id", expl["row_index"].map(X_te["child_id"]))
    expl.insert(2, "prediction_date", expl["row_index"].map(X_te["prediction_date"]))
    expl.insert(3, "priority_rank", expl["row_index"].map(rank_by_index))
    expl.insert(4, "priority_score", expl["row_index"].map(score_by_index))
    expl.to_csv(cfg.out_dir / "tab09_shap_top_children.csv", index=False)

    representative_idx = pd.Index(cases["row_index"].drop_duplicates())
    representative_shap = ex.explain_batch(X_te.loc[representative_idx, primary_cols], top_k=5)
    representative_shap = cases[
        ["row_index", "case_type", "selection_rule", "child_id", "prediction_date",
         "outcome_label", "primary_score", "primary_rank"]
    ].merge(representative_shap, on="row_index", how="left")
    representative_shap["explanation_kind"] = "feature_attribution_non_causal"
    representative_shap["shap_scale"] = "raw_model_log_odds"
    representative_shap.to_csv(
        cfg.out_dir / "tab09_shap_representative_cases.csv", index=False
    )

    manifest = {
        "timestamp_utc": timestamp_utc,
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "data_path": str(cfg.data_path),
        "seed": cfg.seed,
        "split_kind": split.kind,
        "split_sizes": {
            "train_all_visits": len(tr),
            "val_all_visits": len(va_all), "val_index_visits": len(va),
            "test_all_visits": len(te_all), "test_index_visits": len(te),
        },
        "evaluation_unit": cfg.evaluation_unit,
        "validation_unit": cfg.validation_unit,
        "index_visit_rule": ("latest eligible visit per child" if cfg.split_kind == "grouped"
                             else "first eligible visit per child after cutoff"),
        "n_children": {k: len(v) for k, v in split.child_ids.items()},
        "child_ids": split.child_ids,          # DEC-003: split dapat direproduksi persis
        "prevalence_test": round(float(y_te.mean()), 4),
        "primary_model": cfg.primary_model,
        "selection_rule": cfg.selection_rule,
        "operating_k": cfg.operating_k,
        "b1_weights": {"w_haz": b1.w_haz, "w_slope": b1.w_slope},
        "b1_preprocessing_fitted_on": "train",
        "lgb_params": LGB_PARAMS,
        "best_iteration": {n: int(m.best_iteration_ or LGB_PARAMS["n_estimators"])
                           for n, (m, _) in models.items()},
        "shap_artifacts_written": True,
        "primary_model_path": str(model_path),
        "model_artifact_metadata": artifact_metadata,
        "n_features": {"snapshot": len(snap), "snapshot+trajectory": len(snap_traj), "full": len(full)},
    }
    (cfg.out_dir / "tab04_manifest.json").write_text(json.dumps(manifest, indent=2))

    return {"table": table, "rule_table": rule_table, "manifest": manifest, "drops": drops,
            "models": models, "scores": scores, "y_test": y_te, "X_test": X_te,
            "primary_model": primary_model, "primary_cols": primary_cols,
            "model_path": model_path, "representative_cases": cases}


def headline(table: pd.DataFrame, k_pct: int = 20) -> str:
    """Kalimat dampak untuk paper 4.2 dan video, dirakit dari angka nyata."""
    col = f"recall@{k_pct}%"
    b0 = float(table.loc[table["model"] == "B0_haz_only", col].iloc[0])
    m2 = float(table.loc[table["model"] == "M2_plus_trajectory", col].iloc[0])
    return (
        f"Pada skenario kapasitas tindak lanjut sebesar {k_pct}% dari anak yang dipantau "
        f"(satu kunjungan indeks per anak), "
        f"pendekatan berbasis lintasan menangkap {m2:.1%} kasus deteriorasi pada kohort "
        f"sintetis, dibandingkan {b0:.1%} bila prioritas hanya didasarkan pada HAZ terkini. "
        f"Angka kapasitas {k_pct}% adalah skenario operasional, belum dikonfirmasi lapangan."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, default=ExperimentConfig.data_path)
    ap.add_argument("--out", type=Path, default=ExperimentConfig.out_dir)
    ap.add_argument("--seed", type=int, default=ExperimentConfig.seed)
    ap.add_argument("--split", choices=["grouped", "temporal"], default="grouped")
    args = ap.parse_args()

    cfg = ExperimentConfig(data_path=args.data, out_dir=args.out, seed=args.seed, split_kind=args.split)
    res = run(cfg)

    cols = ["model", "auprc", "recall@20%", "precision@20%", "lift@20%",
            "recall@10%", "f1", "score_type"]
    print("\n=== TAB-04 perbandingan model ranking (test set) ===")
    print(res["table"][cols].to_string(index=False))
    print("\n=== aturan biner (metrik klasifikasi saja) ===")
    print(res["rule_table"][["model", "precision", "recall", "f1", "operating_point"]].to_string(index=False))
    print("\n=== baris yang dibuang saat pelabelan ===")
    print(res["drops"].to_string(index=False))
    print("\n" + headline(res["table"]))
    print(f"\nArtefak tersimpan di: {cfg.out_dir}")
    print("Salin angka ke EXPERIMENTS.md dari file CSV, bukan dari layar ini.")


if __name__ == "__main__":
    main()
