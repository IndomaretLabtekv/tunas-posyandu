"""Definisi target prospektif dan aturan kasus tepi (DEC-010).

Satu-satunya sumber kebenaran untuk label. Jangan mendefinisikan ulang di
notebook -- kalau definisinya berubah, ubah di sini supaya seluruh eksperimen
ikut berubah dan tercatat di git.

Definisi:

    Deteriorasi terjadi bila pada kunjungan tindak lanjut dalam jendela
    3 bulan (+/- 6 minggu) setelah t, anak mengalami penurunan HAZ >= 0.5 SD
    dibanding t, ATAU melintasi ambang HAZ -2 ke arah lebih buruk.

Ambang 0.5 SD adalah *operational deterioration threshold* untuk prototipe,
bukan ambang klinis tervalidasi. Kalibrasi bersama ahli gizi -> Future Work.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

HORIZON_DAYS = 91          # ~3 bulan
WINDOW_TOLERANCE_DAYS = 42  # +/- 6 minggu
HAZ_DROP_THRESHOLD = 0.5
STUNTING_THRESHOLD = -2.0

# Alasan sebuah baris dibuang. Distribusinya WAJIB dilaporkan di paper --
# jumlah baris yang hilang adalah bagian dari hasil, bukan detail teknis.
DROP_REASONS = {
    "baseline_missing_haz",
    "baseline_age_out_of_mvp_range",
    "no_followup_in_window",
    "followup_missing_haz",
    "followup_age_out_of_mvp_range",
    "followup_age_not_after_baseline",
}


@dataclass(frozen=True)
class LabelResult:
    label: pd.Series          # 1/0, NaN untuk baris yang dibuang
    drop_reason: pd.Series    # str atau NaN
    followup_idx: pd.Series   # indeks kunjungan tindak lanjut yang dipakai


def _is_deteriorated(haz_t: float, haz_next: float) -> bool:
    dropped = (haz_t - haz_next) >= HAZ_DROP_THRESHOLD
    crossed = (haz_t >= STUNTING_THRESHOLD) and (haz_next < STUNTING_THRESHOLD)
    return bool(dropped or crossed)


def label_visits(
    df: pd.DataFrame,
    *,
    max_age_days: int = 730,
    horizon_days: int = HORIZON_DAYS,
    tolerance_days: int = WINDOW_TOLERANCE_DAYS,
) -> LabelResult:
    """Beri label prospektif pada setiap kunjungan.

    Kolom wajib: `child_id`, `visit_date` (datetime), `age_days`, `haz`.

    Aturan kasus tepi (DEC-010):
      - tidak ada kunjungan di dalam jendela          -> dibuang
      - lebih dari satu kunjungan di dalam jendela    -> pakai yang terdekat ke horizon
      - kunjungan hanya di luar jendela               -> dibuang, tanpa ekstrapolasi
      - anak melewati batas usia MVP di dalam jendela -> dibuang
      - follow-up ada tapi HAZ kosong                 -> dibuang
      - anak sudah severely stunted pada t            -> TETAP disertakan
    """
    if horizon_days <= 0:
        raise ValueError("horizon_days harus lebih besar dari 0.")
    if tolerance_days < 0 or tolerance_days >= horizon_days:
        raise ValueError(
            "tolerance_days harus >= 0 dan lebih kecil dari horizon_days; "
            "kalau tidak, kunjungan saat ini bisa terpilih sebagai follow-up dirinya sendiri."
        )

    required = {"child_id", "visit_date", "age_days", "haz"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom hilang: {sorted(missing)}")

    if not df.index.is_unique:
        raise ValueError(
            "Index DataFrame harus unik sebelum pelabelan; index duplikat membuat "
            "satu assignment mengenai beberapa baris sekaligus."
        )

    d = df.copy()
    d["visit_date"] = pd.to_datetime(d["visit_date"], errors="coerce")
    if d["visit_date"].isna().any():
        n = int(d["visit_date"].isna().sum())
        raise ValueError(
            f"Terdapat {n} baris dengan visit_date kosong atau tidak valid. "
            "Bersihkan di tahap ingest, jangan dibiarkan lolos ke pelabelan."
        )
    child = d["child_id"].astype("string")
    if child.isna().any() or child.str.strip().eq("").any():
        raise ValueError("Terdapat child_id kosong atau hanya berisi spasi.")
    d = d.sort_values(["child_id", "visit_date"])

    label = pd.Series(np.nan, index=d.index, dtype="float64")
    reason = pd.Series(pd.NA, index=d.index, dtype="object")
    fu_idx = pd.Series(pd.NA, index=d.index, dtype="object")

    lo, hi = horizon_days - tolerance_days, horizon_days + tolerance_days

    for _, grp in d.groupby("child_id", sort=False):
        idx = grp.index.to_numpy()
        dates = grp["visit_date"].to_numpy()
        ages = grp["age_days"].to_numpy(dtype=float)
        hazs = grp["haz"].to_numpy(dtype=float)

        for i, row_idx in enumerate(idx):
            if not np.isfinite(hazs[i]):
                reason.loc[row_idx] = "baseline_missing_haz"
                continue
            if not np.isfinite(ages[i]) or ages[i] < 0 or ages[i] > max_age_days:
                reason.loc[row_idx] = "baseline_age_out_of_mvp_range"
                continue

            gaps = (dates - dates[i]).astype("timedelta64[D]").astype(float)
            in_window = np.where((gaps >= lo) & (gaps <= hi))[0]
            if in_window.size == 0:
                reason.loc[row_idx] = "no_followup_in_window"
                continue

            # terdekat ke titik horizon
            j = in_window[np.argmin(np.abs(gaps[in_window] - horizon_days))]

            if not np.isfinite(ages[j]) or ages[j] < 0 or ages[j] > max_age_days:
                reason.loc[row_idx] = "followup_age_out_of_mvp_range"
                continue
            if ages[j] <= ages[i]:
                # Usia anak tidak mungkin tetap atau berkurang pada kunjungan
                # berikutnya -- ini korupsi data, bukan kasus tepi klinis.
                reason.loc[row_idx] = "followup_age_not_after_baseline"
                continue
            if not np.isfinite(hazs[j]):
                reason.loc[row_idx] = "followup_missing_haz"
                continue

            label.loc[row_idx] = float(_is_deteriorated(hazs[i], hazs[j]))
            fu_idx.loc[row_idx] = idx[j]

    return LabelResult(
        label=label.reindex(df.index),
        drop_reason=reason.reindex(df.index),
        followup_idx=fu_idx.reindex(df.index),
    )


def attach_labels(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Versi praktis: kembalikan salinan df dengan kolom label terpasang.

    `label_available_date` = tanggal kunjungan tindak lanjut yang membentuk
    label. Kolom ini WAJIB dipakai oleh temporal split: label pada baris
    bertanggal sebelum cutoff belum tentu sudah diketahui pada saat cutoff,
    dan memakainya untuk melatih adalah kebocoran masa depan.
    """
    res = label_visits(df, **kwargs)
    out = df.copy()
    out["y_deterioration"] = res.label
    out["drop_reason"] = res.drop_reason
    out["followup_idx"] = res.followup_idx
    dates = pd.to_datetime(df["visit_date"], errors="coerce")
    out["label_available_date"] = res.followup_idx.map(
        lambda i: dates.loc[i] if pd.notna(i) else pd.NaT
    )
    return out


def drop_report(df_labeled: pd.DataFrame) -> pd.DataFrame:
    """Rekap baris yang dibuang -- masuk paper section 4.2."""
    total = len(df_labeled)
    counts = df_labeled["drop_reason"].value_counts(dropna=True)
    kept = int(df_labeled["y_deterioration"].notna().sum())
    rows = [{"reason": "kept", "n": kept, "pct": round(100 * kept / total, 2)}]
    for reason, n in counts.items():
        rows.append({"reason": reason, "n": int(n), "pct": round(100 * n / total, 2)})
    return pd.DataFrame(rows)
