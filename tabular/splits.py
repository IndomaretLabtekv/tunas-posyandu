"""Split data bebas kebocoran (DEC-003).

Dua sumber kebocoran yang dicegah di sini:

1.  Kebocoran identitas. Satu anak menyumbang banyak baris kunjungan. Random
    split per baris menempatkan kunjungan anak yang sama di train dan test,
    sehingga model mengenali individu dan metrik jadi terlalu optimistis.
    -> seluruh baris satu `child_id` selalu berada pada split yang sama.

2.  Kebocoran waktu. Model tidak boleh melihat masa depan.
    -> tersedia temporal holdout: train pada periode awal, test pada periode
       akhir kohort.

Verifikasi kebocoran ada di `tests/test_splits.py` dan HARUS dijalankan
sebelum angka apa pun masuk paper (TAB-03).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Split:
    train: pd.Index
    val: pd.Index
    test: pd.Index
    kind: str
    seed: int | None
    child_ids: dict[str, list]

    def summary(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"split": k, "n_rows": len(v), "n_children": len(self.child_ids[k])}
                for k, v in (("train", self.train), ("val", self.val), ("test", self.test))
            ]
        )


def _validate_frame(df: pd.DataFrame, child_col: str, date_col: str | None = None) -> None:
    if df.empty:
        raise ValueError("DataFrame kosong.")
    if not df.index.is_unique:
        raise ValueError("Index DataFrame harus unik sebelum di-split.")
    if child_col not in df.columns:
        raise ValueError(f"Kolom {child_col!r} tidak ada.")
    child = df[child_col].astype("string")
    if child.isna().any() or child.str.strip().eq("").any():
        raise ValueError(f"Terdapat {child_col} kosong atau hanya berisi spasi.")
    if date_col is not None:
        if date_col not in df.columns:
            raise ValueError(f"Kolom {date_col!r} tidak ada.")
        if pd.to_datetime(df[date_col], errors="coerce").isna().any():
            raise ValueError(f"Terdapat {date_col} kosong atau tidak valid.")


def _assert_nonempty(split_idx: dict[str, pd.Index]) -> None:
    empty = [k for k, v in split_idx.items() if len(v) == 0]
    if empty:
        raise ValueError(
            f"Split kosong: {empty}. Jumlah anak kemungkinan terlalu sedikit "
            "untuk fraksi yang diminta."
        )


def grouped_split(
    df: pd.DataFrame,
    *,
    child_col: str = "child_id",
    train_frac: float = 0.6,
    val_frac: float = 0.2,
    seed: int = 42,
) -> Split:
    """Split acak pada level ANAK, bukan level baris."""
    if not 0 < train_frac < 1 or not 0 <= val_frac < 1:
        raise ValueError("Fraksi tidak valid.")
    if train_frac + val_frac >= 1:
        raise ValueError("train_frac + val_frac harus < 1 agar test tidak kosong.")
    _validate_frame(df, child_col)

    children = np.array(sorted(df[child_col].unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(children)

    n = len(children)
    n_train = int(round(train_frac * n))
    n_val = int(round(val_frac * n))
    groups = {
        "train": children[:n_train],
        "val": children[n_train : n_train + n_val],
        "test": children[n_train + n_val :],
    }

    idx = {k: df.index[df[child_col].isin(v)] for k, v in groups.items()}
    _assert_nonempty(idx)
    return Split(
        train=idx["train"],
        val=idx["val"],
        test=idx["test"],
        kind="grouped",
        seed=seed,
        child_ids={k: sorted(v.tolist()) for k, v in groups.items()},
    )


def temporal_split(
    df: pd.DataFrame,
    *,
    date_col: str = "visit_date",
    child_col: str = "child_id",
    test_start: str | pd.Timestamp | None = None,
    test_frac: float = 0.2,
    val_frac: float = 0.2,
    seed: int = 42,
) -> Split:
    """Temporal holdout: test = periode terakhir kohort.

    Anak yang muncul di kedua periode tetap boleh muncul di train dan test,
    karena di sini yang diuji adalah generalisasi ke WAKTU, bukan ke individu.
    Itu skenario penerapan nyata: model dilatih pada data historis lalu dipakai
    pada bulan berikutnya. Laporkan kedua jenis split di paper -- keduanya
    menjawab pertanyaan yang berbeda.
    """
    if not 0 < test_frac < 1 or not 0 <= val_frac < 1:
        raise ValueError("test_frac harus di (0,1) dan val_frac di [0,1).")
    _validate_frame(df, child_col, date_col)

    d = df.copy()
    d[date_col] = pd.to_datetime(d[date_col])

    if test_start is None:
        cutoff = d[date_col].quantile(1 - test_frac)
    else:
        cutoff = pd.Timestamp(test_start)

    is_test = d[date_col] >= cutoff
    test_idx = d.index[is_test]
    pool = d.index[~is_test]

    # validation diambil dari pool secara grouped agar tuning bebas kebocoran identitas
    pool_children = np.array(sorted(d.loc[pool, child_col].unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(pool_children)
    n_val = int(round(val_frac * len(pool_children)))
    val_children = set(pool_children[:n_val])

    val_idx = pd.Index([i for i in pool if d.loc[i, child_col] in val_children])
    train_idx = pool.difference(val_idx)
    _assert_nonempty({"train": train_idx, "test": test_idx})

    return Split(
        train=train_idx,
        val=val_idx,
        test=test_idx,
        kind=f"temporal(cutoff={pd.Timestamp(cutoff).date()})",
        seed=seed,
        child_ids={
            "train": sorted(d.loc[train_idx, child_col].unique().tolist()),
            "val": sorted(d.loc[val_idx, child_col].unique().tolist()),
            "test": sorted(d.loc[test_idx, child_col].unique().tolist()),
        },
    )


def assert_no_child_leakage(split: Split) -> None:
    """Gagalkan keras bila ada anak muncul di lebih dari satu split."""
    tr = set(split.child_ids["train"])
    va = set(split.child_ids["val"])
    te = set(split.child_ids["test"])
    overlaps = {
        "train&val": tr & va,
        "train&test": tr & te,
        "val&test": va & te,
    }
    bad = {k: sorted(v)[:5] for k, v in overlaps.items() if v}
    if bad:
        raise AssertionError(f"Kebocoran child_id antar split: {bad}")


def lint_future_feature_names(feature_cols: list[str]) -> None:
    """Lint ringan atas NAMA kolom. BUKAN bukti bebas temporal leakage.

    Hanya menangkap kesalahan paling kentara (kolom masa depan ikut ter-merge).
    Kolom bocor bisa bernama netral seperti `growth_delta` atau `latest_haz`
    dan lolos dari sini. Bukti sebenarnya adalah
    `assert_features_not_future()` di bawah.
    """
    suspicious = [c for c in feature_cols if any(
        tok in c.lower() for tok in ("next", "future", "followup", "_t1", "after")
    )]
    if suspicious:
        raise AssertionError(
            f"Nama kolom menyiratkan data masa depan: {suspicious}. "
            "Periksa ulang feature engineering."
        )


def assert_features_not_future(
    features: pd.DataFrame,
    *,
    prediction_date_col: str = "prediction_date",
    max_source_date_col: str = "max_source_date",
) -> None:
    """Bukti temporal leakage: setiap baris fitur hanya memakai data <= t.

    `features.py` WAJIB mencatat, untuk setiap baris, tanggal kunjungan terbaru
    yang ikut membentuk fiturnya (`max_source_date`). Fungsi ini memverifikasi
    tanggal itu tidak pernah melewati tanggal prediksi. Inilah yang memenuhi
    TAB-03 / C-B4 -- lint nama kolom saja tidak cukup.
    """
    for col in (prediction_date_col, max_source_date_col):
        if col not in features.columns:
            raise ValueError(
                f"Kolom {col!r} tidak ada. features.py harus mencatat provenance "
                "tanggal agar klaim bebas kebocoran dapat diuji."
            )
    pred = pd.to_datetime(features[prediction_date_col], errors="coerce")
    src = pd.to_datetime(features[max_source_date_col], errors="coerce")
    # Perbandingan dengan NaT selalu False, jadi tanggal kosong akan lolos diam-diam.
    if pred.isna().any() or src.isna().any():
        raise ValueError(
            f"{prediction_date_col} dan {max_source_date_col} tidak boleh kosong "
            "atau tidak valid -- baris seperti itu tidak dapat dibuktikan bebas kebocoran."
        )
    bad = features.index[src > pred]
    if len(bad):
        raise AssertionError(
            f"{len(bad)} baris memakai data setelah tanggal prediksi. "
            f"Contoh indeks: {list(bad[:5])}"
        )
