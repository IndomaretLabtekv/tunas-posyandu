"""Bangun fitur M2 dari riwayat kunjungan SQLite."""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pandas as pd

from tabular.features import build_features

# ponytail: MVP tidak mengumpulkan fitur kontekstual (imunisasi, ASI, dsb.)
# sehingga np.nanmean sering menerima slice kosong; warning-nya bukan bug.
warnings.filterwarnings("ignore", category=RuntimeWarning, message="Mean of empty slice")

# Kolom yang dipakai model M2 (snapshot + trajectory).
MODEL_COLUMNS = [
    "age_days",
    "sex_is_male",
    "haz_t",
    "weight_kg_t",
    "length_cm_t",
    "haz_missing_t",
    "measured_by_cv_t",
    "n_prior_visits",
    "days_since_first_visit",
    "visit_gap_days_t",
    "visit_gap_mean",
    "haz_slope_per_month",
    "haz_delta_1visit",
    "haz_delta_3months",
    "haz_min_to_date",
    "haz_max_to_date",
    "haz_range_to_date",
    "haz_std_to_date",
    "n_consecutive_declines",
    "ever_stunted_to_date",
    "months_since_haz_peak",
    "length_velocity_cm_per_month",
]


def _visit_row_to_measured_by_cv(mode: str) -> float:
    return 1.0 if mode == "measurement" else 0.0


def visits_to_dataframe(visits: list[dict[str, Any]]) -> pd.DataFrame:
    """Ubah daftar kunjungan dari store menjadi DataFrame siap fitur.

    `visits` diharapkan memiliki kolom: child_id, child_sex, age_days,
    measured_at, mode, length_cm, haz.
    """
    if not visits:
        return pd.DataFrame()
    rows = []
    for v in visits:
        rows.append({
            "child_id": v["child_id"],
            "visit_date": pd.to_datetime(v["measured_at"]),
            "age_days": v["age_days"],
            "sex": v["child_sex"],
            "length_cm": v["length_cm"] if v.get("length_cm") is not None else np.nan,
            "haz": v["haz"] if v.get("haz") is not None else np.nan,
            "measured_by_cv": _visit_row_to_measured_by_cv(v.get("mode", "")),
            # ponytail: kolom kontekstual tidak dikumpulkan MVP -> NaN
            "weight_kg": np.nan,
            "ses_index": np.nan,
            "birth_weight_kg": np.nan,
            "immunization_on_schedule": np.nan,
            "exclusive_bf": np.nan,
            "visit_gap_days": np.nan,
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["child_id", "visit_date"]).reset_index(drop=True)
    return df


def build_model_frame(visits: list[dict[str, Any]]) -> pd.DataFrame:
    """Bangun matriks fitur lengkap (satu baris per kunjungan)."""
    df = visits_to_dataframe(visits)
    if df.empty:
        return pd.DataFrame(columns=MODEL_COLUMNS)
    feats = build_features(df)
    # Hanya ambil kolom yang dikenal model; kolom lain (provenance) dibuang.
    return feats[[c for c in MODEL_COLUMNS if c in feats.columns]]


def latest_visit_index_per_child(
    visits: list[dict[str, Any]], frame: pd.DataFrame
) -> pd.DataFrame:
    """Pilih baris fitur untuk kunjungan terbaru tiap anak."""
    if frame.empty:
        return frame
    latest_ids: set = set()
    by_child: dict[Any, list[tuple[int, pd.Timestamp]]] = {}
    for i, v in enumerate(visits):
        cid = v["child_id"]
        dt = pd.to_datetime(v["measured_at"])
        by_child.setdefault(cid, []).append((i, dt))
    for cid, items in by_child.items():
        latest = max(items, key=lambda x: x[1])[0]
        latest_ids.add(frame.index[latest])
    return frame.loc[frame.index.isin(latest_ids)].copy()
