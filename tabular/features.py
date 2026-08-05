"""Feature engineering tiga blok, bebas kebocoran waktu (T2, TAB-02).

Aturan yang mengikat seluruh modul ini: **fitur pada baris waktu `t` hanya boleh
memakai kunjungan dengan tanggal <= t**. Setiap baris fitur karena itu wajib
membawa provenance:

    prediction_date   tanggal kunjungan yang menjadi titik prediksi
    max_source_date   tanggal terbaru yang ikut membentuk fitur baris ini

`tabular.splits.assert_features_not_future()` memverifikasi
`max_source_date <= prediction_date` untuk setiap baris. Tanpa kedua kolom itu,
klaim bebas kebocoran (C-B4/TAB-03) tidak dapat dibuktikan -- lint nama kolom
saja tidak cukup.

Tiga blok fitur dipisah agar dapat diablasi (TAB-05, DEC-002):

    SNAPSHOT     kondisi pada kunjungan t saja -- ini yang dimiliki pendekatan
                 eksisting berbasis ambang tunggal
    TRAJECTORY   riwayat pertumbuhan lintas kunjungan <= t -- klaim kebaruan
                 paper bergantung pada blok ini memberi nilai tambah
    CONTEXTUAL   faktor risiko kontekstual yang sah diketahui pada t

Ablasi M1 -> M2 -> M3 membandingkan SNAPSHOT, +TRAJECTORY, +CONTEXTUAL. Kalau
peningkatannya kecil, laporkan apa adanya: pembahasan trade-off yang jujur
lebih bernilai daripada klaim yang tidak didukung angka.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DAYS_PER_MONTH = 30.4375

SNAPSHOT_FEATURES = [
    "age_days",
    "sex_is_male",
    "haz_t",
    "weight_kg_t",
    "length_cm_t",
    "haz_missing_t",
    "measured_by_cv_t",
]

TRAJECTORY_FEATURES = [
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

CONTEXTUAL_FEATURES = [
    "ses_index",
    "birth_weight_kg",
    "immunization_on_schedule_t",
    "immunization_on_schedule_rate_to_date",
    "exclusive_bf_known",
    "exclusive_bf_positive",
]

FEATURE_BLOCKS = {
    "snapshot": SNAPSHOT_FEATURES,
    "trajectory": TRAJECTORY_FEATURES,
    "contextual": CONTEXTUAL_FEATURES,
}

REQUIRED_COLUMNS = {
    "child_id", "visit_date", "age_days", "sex", "length_cm", "haz",
}


def feature_columns(blocks: list[str] | None = None) -> list[str]:
    """Daftar kolom fitur untuk kombinasi blok tertentu (dipakai ablasi)."""
    blocks = blocks or list(FEATURE_BLOCKS)
    unknown = set(blocks) - set(FEATURE_BLOCKS)
    if unknown:
        raise ValueError(f"Blok tidak dikenal: {sorted(unknown)}")
    return [c for b in blocks for c in FEATURE_BLOCKS[b]]


def _slope_per_month(days: np.ndarray, values: np.ndarray) -> float:
    """Kemiringan regresi linear HAZ terhadap waktu, dalam SD per bulan."""
    mask = np.isfinite(values)
    if mask.sum() < 2:
        return np.nan
    x = days[mask] / DAYS_PER_MONTH
    y = values[mask]
    if np.ptp(x) < 1e-9:
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def _consecutive_declines(values: np.ndarray) -> int:
    """Berapa kali berturut-turut HAZ turun sampai titik terakhir."""
    v = values[np.isfinite(values)]
    n = 0
    for i in range(len(v) - 1, 0, -1):
        if v[i] < v[i - 1]:
            n += 1
        else:
            break
    return n


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Bangun matriks fitur, satu baris per kunjungan.

    Untuk setiap baris `t`, seluruh agregat dihitung dari kunjungan anak yang
    sama dengan `visit_date <= t`. Baris kunjungan pertama tetap dihasilkan
    (fitur lintasan kosong), karena membuangnya akan menghapus justru anak yang
    baru terdaftar -- kelompok yang penting bagi produk.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Kolom hilang: {sorted(missing)}")
    if not df.index.is_unique:
        raise ValueError("Index DataFrame harus unik.")

    d = df.copy()
    d["visit_date"] = pd.to_datetime(d["visit_date"], errors="coerce")
    if d["visit_date"].isna().any():
        raise ValueError("Terdapat visit_date kosong atau tidak valid.")
    d = d.sort_values(["child_id", "visit_date"])

    has = {c: (c in d.columns) for c in
           ("weight_kg", "measured_by_cv", "ses_index", "birth_weight_kg",
            "immunization_on_schedule", "exclusive_bf", "visit_gap_days")}

    out = []
    for _, grp in d.groupby("child_id", sort=False):
        idx = grp.index.to_numpy()
        dates = grp["visit_date"].to_numpy()
        days = (dates - dates[0]).astype("timedelta64[D]").astype(float)
        hazs = grp["haz"].to_numpy(dtype=float)
        lens = grp["length_cm"].to_numpy(dtype=float)

        for i, row_idx in enumerate(idx):
            row = grp.loc[row_idx]
            # Jendela ketat: hanya kunjungan ke-0..i. Inilah satu-satunya tempat
            # kebocoran waktu bisa masuk, jadi tidak ada slicing lain di bawah.
            h_hist = hazs[: i + 1]
            d_hist = days[: i + 1]
            l_hist = lens[: i + 1]
            h_obs = h_hist[np.isfinite(h_hist)]

            f = {
                "row_index": row_idx,   # index baris asli -> penyambung ke label
                "child_id": row["child_id"],
                "visit_index": i,
                "prediction_date": row["visit_date"],
                "max_source_date": grp["visit_date"].iloc[i],  # == prediction_date
                # --- snapshot
                "age_days": float(row["age_days"]),
                "sex_is_male": float(str(row["sex"]).strip().upper().startswith("M")),
                "haz_t": float(hazs[i]) if np.isfinite(hazs[i]) else np.nan,
                "length_cm_t": float(lens[i]) if np.isfinite(lens[i]) else np.nan,
                "weight_kg_t": float(row["weight_kg"]) if has["weight_kg"] else np.nan,
                "haz_missing_t": float(not np.isfinite(hazs[i])),
                "measured_by_cv_t": float(row["measured_by_cv"]) if has["measured_by_cv"] else np.nan,
                # --- trajectory
                "n_prior_visits": float(i),
                "days_since_first_visit": float(d_hist[-1]),
                "visit_gap_days_t": float(d_hist[-1] - d_hist[-2]) if i >= 1 else np.nan,
                "visit_gap_mean": float(np.mean(np.diff(d_hist))) if i >= 1 else np.nan,
                "haz_slope_per_month": _slope_per_month(d_hist, h_hist),
                "haz_min_to_date": float(h_obs.min()) if h_obs.size else np.nan,
                "haz_max_to_date": float(h_obs.max()) if h_obs.size else np.nan,
                "haz_range_to_date": float(h_obs.max() - h_obs.min()) if h_obs.size > 1 else np.nan,
                "haz_std_to_date": float(h_obs.std(ddof=1)) if h_obs.size > 1 else np.nan,
                "n_consecutive_declines": float(_consecutive_declines(h_hist)),
                "ever_stunted_to_date": float((h_obs < -2).any()) if h_obs.size else np.nan,
            }

            # Delta terhadap pengamatan HAZ sebelumnya yang tersedia.
            prev = h_hist[:-1][np.isfinite(h_hist[:-1])]
            f["haz_delta_1visit"] = (
                float(hazs[i] - prev[-1]) if np.isfinite(hazs[i]) and prev.size else np.nan
            )

            # Delta terhadap pengamatan terdekat ~3 bulan lalu (jendela 60-120 hari).
            f["haz_delta_3months"] = np.nan
            if np.isfinite(hazs[i]):
                back = d_hist[-1] - d_hist[:-1]
                cand = np.where((back >= 60) & (back <= 120) & np.isfinite(h_hist[:-1]))[0]
                if cand.size:
                    j = cand[np.argmin(np.abs(back[cand] - 91))]
                    f["haz_delta_3months"] = float(hazs[i] - h_hist[j])

            # Jarak waktu sejak HAZ tertinggi -- proksi lamanya penurunan berjalan.
            f["months_since_haz_peak"] = np.nan
            fin = np.where(np.isfinite(h_hist))[0]
            if fin.size:
                peak = fin[np.argmax(h_hist[fin])]
                f["months_since_haz_peak"] = float((d_hist[-1] - d_hist[peak]) / DAYS_PER_MONTH)

            # Kecepatan pertumbuhan panjang badan pada kunjungan terakhir.
            f["length_velocity_cm_per_month"] = np.nan
            lfin = np.where(np.isfinite(l_hist))[0]
            if lfin.size >= 2:
                a, b = lfin[-2], lfin[-1]
                dt = (d_hist[b] - d_hist[a]) / DAYS_PER_MONTH
                if dt > 1e-6:
                    f["length_velocity_cm_per_month"] = float((l_hist[b] - l_hist[a]) / dt)

            # --- contextual
            f["ses_index"] = float(row["ses_index"]) if has["ses_index"] else np.nan
            f["birth_weight_kg"] = float(row["birth_weight_kg"]) if has["birth_weight_kg"] else np.nan
            if has["immunization_on_schedule"]:
                imm = grp["immunization_on_schedule"].to_numpy()[: i + 1].astype(float)
                f["immunization_on_schedule_t"] = float(imm[-1])
                f["immunization_on_schedule_rate_to_date"] = float(np.nanmean(imm))
            else:
                f["immunization_on_schedule_t"] = np.nan
                f["immunization_on_schedule_rate_to_date"] = np.nan

            # `exclusive_bf` kosong sebelum 180 hari BUKAN data hilang, melainkan
            # informasi yang memang belum tersedia. Dipisah jadi dua kolom agar
            # model membedakan "belum diketahui" dari "diketahui negatif".
            if has["exclusive_bf"]:
                val = row["exclusive_bf"]
                known = pd.notna(val)
                f["exclusive_bf_known"] = float(known)
                f["exclusive_bf_positive"] = float(bool(val)) if known else 0.0
            else:
                f["exclusive_bf_known"] = np.nan
                f["exclusive_bf_positive"] = np.nan

            out.append(f)

    feats = pd.DataFrame(out).set_index("row_index")
    feats.index.name = df.index.name
    # Kembalikan pada urutan baris df asli agar dapat langsung disandingkan
    # dengan keluaran tabular.target tanpa merge manual.
    return feats.reindex(df.index)


def build_dataset(df: pd.DataFrame, blocks: list[str] | None = None) -> pd.DataFrame:
    """Fitur + kolom identitas + provenance, siap digabung dengan label."""
    feats = build_features(df)
    keep = ["child_id", "visit_index", "prediction_date", "max_source_date"]  # provenance wajib
    return feats[keep + feature_columns(blocks)]


def missingness_report(feats: pd.DataFrame) -> pd.DataFrame:
    """Persentase nilai kosong per fitur -- dilaporkan di TAB-02.

    Fitur lintasan wajar kosong pada kunjungan pertama; itu bukan cacat data,
    melainkan konsekuensi anak yang baru terdaftar. Yang perlu dijelaskan di
    paper adalah bagaimana model menanganinya, bukan menyembunyikan barisnya.
    """
    cols = [c for c in feats.columns if c in feature_columns()]
    rows = [
        {
            "feature": c,
            "block": next(b for b, v in FEATURE_BLOCKS.items() if c in v),
            "missing_pct": round(100 * float(feats[c].isna().mean()), 2),
        }
        for c in cols
    ]
    return pd.DataFrame(rows).sort_values(["block", "missing_pct"], ascending=[True, False])
