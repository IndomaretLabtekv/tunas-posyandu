"""Konversi panjang badan <-> HAZ berbasis tabel LMS WHO (DEC-009).

Modul ini sengaja TIDAK memuat angka LMS di dalam kode. Tabel diambil dari
WHO Child Growth Standards dan disimpan di `data/who/lhfa_lms.csv` dengan skema
kanonik berikut:

    sex,age_days,L,M,S
    M,0,1,49.8842,0.03795
    ...

Lihat `scripts/prepare_who_tables.py` untuk mengubah berkas WHO asli menjadi
skema di atas. Alasan tabel tidak di-hardcode: nilai LMS adalah data rujukan
resmi; menyalinnya dari ingatan atau sumber sekunder adalah cara paling mudah
membuat seluruh angka di paper salah tanpa ketahuan.

Catatan metodologis yang relevan untuk paper:

1.  Untuk length/height-for-age, WHO menetapkan L = 1, sehingga
    Z = (X - M) / (M * S). Implementasi di bawah tetap memakai bentuk umum
    Box-Cox agar dapat dipakai ulang untuk indikator lain (WAZ/WHZ) tanpa
    mengubah kode.
2.  HAZ TIDAK mengalami penyesuaian ekor distribusi. Koreksi |Z| > 3 hanya
    berlaku untuk indikator berbasis berat. Jangan menyalin logika itu ke sini.
3.  MVP Tunas hanya mendukung protokol recumbent (DEC-005), sehingga rentang
    usia yang sah adalah 0-23 bulan penuh. Usia di luar rentang ditolak, bukan
    diekstrapolasi.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

# MVP: recumbent length, 0-23 bulan penuh (DEC-005).
MIN_AGE_DAYS = 0
MAX_AGE_DAYS = 730  # 24 bulan * 30.4375 hari, dibulatkan ke bawah

DEFAULT_TABLE = Path(__file__).resolve().parents[1] / "data" / "who" / "lhfa_lms.csv"

REQUIRED_COLUMNS = {"sex", "age_days", "L", "M", "S"}


class AgeOutOfRangeError(ValueError):
    """Usia berada di luar rentang yang didukung MVP."""


class TableNotFoundError(FileNotFoundError):
    """Tabel LMS WHO belum disiapkan."""


@dataclass(frozen=True)
class LMS:
    L: float
    M: float
    S: float


@lru_cache(maxsize=4)
def load_table(path: str | Path = DEFAULT_TABLE) -> pd.DataFrame:
    """Muat tabel LMS kanonik. Hasil di-cache karena dipakai per baris."""
    path = Path(path)
    if not path.exists():
        raise TableNotFoundError(
            f"Tabel LMS tidak ditemukan di {path}. "
            "Jalankan `python -m scripts.prepare_who_tables --help` lebih dulu."
        )
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Kolom hilang pada {path}: {sorted(missing)}")

    df["sex"] = df["sex"].astype(str).str.upper().str[0]
    if not set(df["sex"]).issubset({"M", "F"}):
        raise ValueError("Kolom `sex` harus berisi M/F setelah normalisasi.")

    df = df.sort_values(["sex", "age_days"]).reset_index(drop=True)
    return df


def _validate_age(age_days: float) -> None:
    if not np.isfinite(age_days):
        raise AgeOutOfRangeError("Usia tidak boleh NaN/inf.")
    if age_days < MIN_AGE_DAYS or age_days > MAX_AGE_DAYS:
        raise AgeOutOfRangeError(
            f"Usia {age_days} hari di luar rentang MVP "
            f"[{MIN_AGE_DAYS}, {MAX_AGE_DAYS}] hari (protokol recumbent, DEC-005)."
        )


def get_lms(sex: str, age_days: float, table: pd.DataFrame | None = None) -> LMS:
    """Ambil parameter LMS, diinterpolasi linear antar hari bila perlu.

    WHO menerbitkan tabel harian untuk 0-1856 hari, sehingga interpolasi
    biasanya hanya menutup usia pecahan hari.
    """
    _validate_age(age_days)
    sex = str(sex).strip().upper()
    if sex in {"MALE", "L", "LAKI-LAKI"}:
        sex = "M"
    elif sex in {"FEMALE", "P", "PEREMPUAN"}:
        sex = "F"
    if sex not in {"M", "F"}:
        raise ValueError(f"Jenis kelamin tidak dikenal: {sex!r} (harap 'M' atau 'F').")

    df = load_table() if table is None else table
    sub = df[df["sex"] == sex]
    if sub.empty:
        raise ValueError(f"Tabel tidak memuat data untuk sex={sex!r}.")

    ages = sub["age_days"].to_numpy(dtype=float)
    if age_days < ages.min() or age_days > ages.max():
        raise AgeOutOfRangeError(
            f"Usia {age_days} hari di luar cakupan tabel "
            f"[{ages.min()}, {ages.max()}]."
        )

    return LMS(
        L=float(np.interp(age_days, ages, sub["L"].to_numpy(dtype=float))),
        M=float(np.interp(age_days, ages, sub["M"].to_numpy(dtype=float))),
        S=float(np.interp(age_days, ages, sub["S"].to_numpy(dtype=float))),
    )


def haz(length_cm: float, sex: str, age_days: float, table: pd.DataFrame | None = None) -> float:
    """Panjang badan (cm) -> height-for-age z-score.

    Tanpa penyesuaian ekor distribusi: HAZ tidak dikoreksi pada |Z| > 3.
    """
    if not np.isfinite(length_cm) or length_cm <= 0:
        raise ValueError(f"Panjang badan tidak valid: {length_cm!r}")

    p = get_lms(sex, age_days, table)
    if abs(p.L) < 1e-12:  # kasus L == 0 -> bentuk logaritmik
        return float(np.log(length_cm / p.M) / p.S)
    return float(((length_cm / p.M) ** p.L - 1.0) / (p.L * p.S))


def length_from_haz(z: float, sex: str, age_days: float, table: pd.DataFrame | None = None) -> float:
    """Inverse dari `haz`. Dipakai generator data sintetis (DATA_CARD 2.3)."""
    if not np.isfinite(z):
        raise ValueError(f"Z-score tidak valid: {z!r}")

    p = get_lms(sex, age_days, table)
    if abs(p.L) < 1e-12:
        return float(p.M * np.exp(p.S * z))
    base = 1.0 + p.L * p.S * z
    if base <= 0:
        raise ValueError(
            f"Z-score {z} berada di luar domain inverse LMS pada usia {age_days} hari; "
            "transformasi Box-Cox tidak terdefinisi (akan menghasilkan panjang negatif)."
        )
    return float(p.M * base ** (1.0 / p.L))


def classify(z: float) -> str:
    """Klasifikasi status panjang badan menurut ambang WHO.

    Ini klasifikasi status gizi berdasarkan standar, BUKAN keluaran model.
    Model Tunas memprediksi deteriorasi prospektif (DEC-010), bukan label ini.
    """
    if not np.isfinite(z):
        raise ValueError("Z-score tidak valid.")
    if z < -3.0:
        return "severely_stunted"
    if z < -2.0:
        return "stunted"
    return "normal"


def haz_series(df: pd.DataFrame, table: pd.DataFrame | None = None) -> pd.Series:
    """Versi vektor untuk DataFrame kunjungan.

    Butuh kolom: `sex`, `age_days`, `length_cm`.
    Baris yang gagal (usia di luar rentang, panjang tidak valid) menghasilkan
    NaN dan TIDAK dibuang diam-diam -- pemanggil yang memutuskan.
    """
    tbl = load_table() if table is None else table
    out = []
    for sex, age_days, length_cm in zip(df["sex"], df["age_days"], df["length_cm"]):
        try:
            out.append(haz(float(length_cm), sex, float(age_days), tbl))
        except (ValueError, TypeError, IndexError, AgeOutOfRangeError):
            # Satu baris rusak tidak boleh menggagalkan seluruh batch.
            out.append(np.nan)
    return pd.Series(out, index=df.index, name="haz")
