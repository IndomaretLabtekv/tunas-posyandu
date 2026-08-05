"""Baseline pembanding, seluruhnya menghasilkan skor ranking (DEC-012).

Produk mengurutkan anak, sehingga baseline juga harus dapat mengurutkan --
aturan biner `HAZ < -2` tidak dapat dibandingkan pada Precision@K sama sekali.

    B0  priority = -HAZ_t
        Proxy baseline prioritisasi berdasarkan HAZ terkini: makin rendah HAZ,
        makin tinggi prioritas. Disebut *proxy* -- bukan "praktik eksisting" --
        sampai alur kerja itu dikonfirmasi lewat wawancara kader/petugas gizi.

    B1  priority = w1*(-HAZ_t) + w2*(-slope_HAZ)
        Bobot ditentukan pada VALIDATION split, tidak pernah pada test.

    B2  logistic regression atas fitur snapshot.

    RULE  aturan biner HAZ_t < -2, hanya untuk metrik klasifikasi.

Seluruhnya dievaluasi pada target dan split yang identik dengan LightGBM
(DEC-002), sehingga selisihnya benar-benar mengukur nilai tambah pendekatan,
bukan perbedaan tugas.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from tabular.evaluate import recall_at_k

STUNTING_THRESHOLD = -2.0


@dataclass(frozen=True)
class B0Model:
    """B0 -- proxy baseline prioritisasi berdasarkan status HAZ terkini.

    Disebut *proxy*, bukan "praktik eksisting", sampai alur kerja tersebut
    benar-benar dikonfirmasi lewat wawancara kader/petugas gizi.

    Kebijakan nilai kosong dinyatakan eksplisit: baris tanpa `haz_t` diberi
    skor tetap `missing_score`, bukan diisi median. Mengisi median dari batch
    yang sedang diberi skor membuat peringkat satu anak bergantung pada siapa
    saja yang kebetulan ikut dalam batch itu.

    `missing_score` berupa konstanta (bukan turunan dari batch) agar skor
    sebuah baris selalu sama berapa pun batch-nya. Nilainya jauh di bawah
    rentang HAZ yang mungkin, sehingga efeknya = prioritas terendah, tetapi
    tetap berhingga agar tidak merusak perhitungan metrik.
    """

    missing_score: float = -1e6

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if "haz_t" not in X.columns:
            raise ValueError("B0 membutuhkan kolom `haz_t`.")
        haz = pd.to_numeric(X["haz_t"], errors="coerce")
        s = (-haz).to_numpy(dtype=float)
        return np.where(np.isfinite(s), s, self.missing_score)


def b0_haz_only(X: pd.DataFrame) -> np.ndarray:
    """Antarmuka praktis untuk B0Model default."""
    return B0Model().predict(X)


@dataclass(frozen=True)
class B1Weights:
    w_haz: float
    w_slope: float


@dataclass(frozen=True)
class B1Model:
    """B1 -- HAZ terkini + kecepatan perubahan.

    Seluruh state preprocessing (imputasi + standardisasi) DIPELAJARI DARI TRAIN
    dan dikunci. Versi sebelumnya menghitung ulang mean/std dari data yang sedang
    diberi skor, sehingga peringkat dua anak bisa berubah hanya karena ada anak
    ketiga dalam batch test. Itu test-distribution leakage dan membuat baseline
    tidak dapat diterapkan secara konsisten.
    """

    w_haz: float
    w_slope: float
    haz_fill: float
    haz_mean: float
    haz_std: float
    slope_fill: float
    slope_mean: float
    slope_std: float

    def _z(self, X: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        haz = pd.to_numeric(X["haz_t"], errors="coerce").fillna(self.haz_fill).to_numpy(float)
        slope = pd.to_numeric(X["haz_slope_per_month"], errors="coerce").fillna(self.slope_fill).to_numpy(float)
        return ((-haz - self.haz_mean) / self.haz_std,
                (-slope - self.slope_mean) / self.slope_std)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        h, s = self._z(X)
        return self.w_haz * h + self.w_slope * s

    @property
    def weights(self) -> B1Weights:
        return B1Weights(self.w_haz, self.w_slope)


def _fit_state(X_train: pd.DataFrame) -> dict:
    """Pelajari imputasi & standardisasi dari TRAIN saja."""
    for col in ("haz_t", "haz_slope_per_month"):
        if col not in X_train.columns:
            raise ValueError(f"B1 membutuhkan kolom `{col}`.")
    haz = pd.to_numeric(X_train["haz_t"], errors="coerce")
    slope = pd.to_numeric(X_train["haz_slope_per_month"], errors="coerce")
    if haz.notna().sum() == 0 or slope.notna().sum() == 0:
        raise ValueError(
            "B1 membutuhkan minimal satu nilai valid untuk HAZ dan slope pada "
            "training set; tanpa itu statistik preprocessing menjadi NaN dan "
            "seluruh skor ikut NaN tanpa pesan yang jelas."
        )
    haz_fill, slope_fill = float(haz.median()), float(slope.median())
    nh = (-haz.fillna(haz_fill)).to_numpy(float)
    ns = (-slope.fillna(slope_fill)).to_numpy(float)
    return {
        "haz_fill": haz_fill, "haz_mean": float(nh.mean()), "haz_std": float(nh.std() or 1.0),
        "slope_fill": slope_fill, "slope_mean": float(ns.mean()), "slope_std": float(ns.std() or 1.0),
    }


def fit_b1(
    X_train: pd.DataFrame, X_val: pd.DataFrame, y_val, *,
    k_frac: float = 0.20, grid: np.ndarray | None = None,
) -> B1Model:
    """Preprocessing dari TRAIN, bobot dari VALIDATION, test hanya predict.

    Memilih bobot di test akan membuat baseline terlihat lebih kuat daripada
    seharusnya -- perbandingan jadi tidak jujur ke arah berlawanan.
    """
    state = _fit_state(X_train)
    grid = np.linspace(0.0, 1.0, 21) if grid is None else grid

    probe = B1Model(w_haz=1.0, w_slope=0.0, **state)
    h, s = probe._z(X_val)

    best_w, best_score = (1.0, 0.0), -np.inf
    for w in grid:
        score = recall_at_k(y_val, (1 - w) * h + w * s, k_frac)
        if np.isfinite(score) and score > best_score:
            best_score, best_w = score, (round(1 - w, 3), round(w, 3))
    return B1Model(w_haz=best_w[0], w_slope=best_w[1], **state)


def b1_haz_slope(X: pd.DataFrame, model: B1Model) -> np.ndarray:
    return model.predict(X)


def make_b2(seed: int = 42) -> Pipeline:
    """B2 -- logistic regression. Imputasi median + standardisasi di dalam
    pipeline agar tidak ada statistik test yang bocor ke pelatihan."""
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)),
    ])


def rule_stunted_now(X: pd.DataFrame) -> np.ndarray:
    """Rule comparator: status stunting saat ini (`HAZ_t < -2`).

    HANYA untuk metrik klasifikasi -- keluarannya 0/1 sehingga tidak dapat
    mengurutkan anak dalam kelompok yang sama (DEC-012).
    """
    haz = pd.to_numeric(X["haz_t"], errors="coerce")
    return (haz < STUNTING_THRESHOLD).fillna(False).to_numpy(dtype=float)
