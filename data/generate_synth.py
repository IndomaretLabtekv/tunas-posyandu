"""Generator kohort kunjungan Posyandu sintetis (TAB-01, DATA_CARD 2.3).

Prinsip desain yang menentukan sah-tidaknya seluruh eksperimen hilir:

1.  **Label TIDAK dibangkitkan dari fitur.** Generator menghasilkan lintasan HAZ
    laten; label deteriorasi dihitung terpisah oleh `tabular.target` dari
    lintasan SETELAH waktu prediksi. Kalau label dibuat dari aturan atas fitur
    input, model hanya menghafal aturan generator dan angka apa pun jadi tidak
    bermakna (DEC-007).

2.  **Faktor kontekstual bersifat probabilistik, bukan deterministik.** SES,
    imunisasi, ASI eksklusif, dan berat lahir menggeser *distribusi* kecepatan
    pertumbuhan, tidak menentukan hasilnya. Tugas model tetap non-trivial.

3.  **Sebagian anak punya change-point.** Lintasan yang berubah arah di tengah
    membuat nilai HAZ terkini saja tidak cukup untuk memprediksi masa depan --
    inilah kondisi yang membuat fitur lintasan punya nilai tambah, dan
    sekaligus yang diuji oleh ablasi M1 -> M2.

4.  **Ketidakhadiran tidak acak (MNAR).** Anak dari keluarga dengan indeks
    sosial ekonomi rendah lebih sering absen, sehingga anak paling berisiko
    justru punya data paling sedikit. Ini kondisi nyata di lapangan dan wajib
    ada agar evaluasi tidak terlalu optimistis.

Batasan yang wajib dinyatakan di paper: generator ini adalah model dunia yang
disederhanakan. Performa di sini membuktikan kelayakan teknis pipeline dan
memungkinkan perbandingan antar pendekatan pada kondisi terkendali -- BUKAN
validitas klinis pada populasi balita nyata.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from tabular.who_lms import MAX_AGE_DAYS, length_from_haz, load_table

DAYS_PER_MONTH = 30.4375


@dataclass
class SynthConfig:
    n_children: int = 1200
    seed: int = 42

    # Distribusi HAZ awal. Dipilih secara heuristik agar statistik simulasi
    # berada pada orde besaran yang serupa dengan angka nasional; BUKAN hasil
    # kalibrasi terhadap data nyata. Verifikasi karakteristiknya lewat TAB-01.
    haz0_mean: float = -0.85
    haz0_sd: float = 1.15

    # Kecepatan perubahan HAZ (SD per bulan) sebelum pengaruh kontekstual.
    velocity_mean: float = -0.015
    velocity_sd: float = 0.045

    # Change-point: sebagian anak berubah arah di tengah pemantauan.
    changepoint_prob: float = 0.30
    changepoint_delta_sd: float = 0.06

    # Bobot faktor kontekstual terhadap kecepatan (bukan terhadap label).
    w_ses: float = 0.020
    w_immunization: float = 0.010
    w_exclusive_bf: float = 0.008
    w_birth_weight: float = 0.012

    # Proses pengukuran.
    length_noise_sd_cm: float = 0.7      # variasi pengukuran manual di lapangan
    weight_noise_sd_kg: float = 0.15
    weight_haz_coupling: float = 0.30    # kaitan berat-kondisi pertumbuhan, moderat

    # Usia paling awal status ASI eksklusif 6 bulan dapat diketahui.
    exclusive_bf_known_after_days: int = 180

    # Jadwal & kehadiran.
    first_visit_age_days_max: int = 90
    visit_interval_days: int = 30
    visit_jitter_days: int = 6
    base_attendance: float = 0.82
    ses_attendance_effect: float = 0.12  # MNAR: SES rendah lebih sering absen
    min_visits: int = 2

    # Data hilang pada kolom terukur.
    missing_length_prob: float = 0.03
    missing_weight_prob: float = 0.05

    # Proporsi kunjungan yang memakai kanal visual (sisanya input manual).
    cv_usage_prob: float = 0.6

    start_date: str = "2024-01-01"
    enrollment_window_days: int = 240


def _sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def validate_config(cfg: SynthConfig) -> None:
    """Cegah konfigurasi yang membuat loop kunjungan tidak maju."""
    if cfg.n_children <= 0:
        raise ValueError("n_children harus > 0.")
    if cfg.min_visits < 2:
        raise ValueError("min_visits harus >= 2 agar lintasan dapat dibentuk.")
    if cfg.visit_interval_days - cfg.visit_jitter_days <= 0:
        raise ValueError(
            "visit_interval_days harus lebih besar daripada visit_jitter_days; "
            "kalau tidak, langkah usia bisa nol atau mundur."
        )
    for name in (
        "changepoint_prob", "base_attendance",
        "missing_length_prob", "missing_weight_prob", "cv_usage_prob",
    ):
        v = getattr(cfg, name)
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{name} harus berada di [0, 1], dapat {v}.")
    if cfg.first_visit_age_days_max < 0:
        raise ValueError("first_visit_age_days_max tidak boleh negatif.")
    if cfg.visit_jitter_days < 0:
        raise ValueError("visit_jitter_days tidak boleh negatif.")
    if cfg.enrollment_window_days < 0:
        raise ValueError("enrollment_window_days tidak boleh negatif.")
    # Cutoff ini yang mencegah kebocoran waktu pada `exclusive_bf`; konfigurasi
    # negatif akan membuka kembali kebocoran yang sudah ditutup.
    if not 0 <= cfg.exclusive_bf_known_after_days <= MAX_AGE_DAYS:
        raise ValueError(
            f"exclusive_bf_known_after_days harus berada di [0, {MAX_AGE_DAYS}]."
        )
    if cfg.length_noise_sd_cm < 0 or cfg.weight_noise_sd_kg < 0:
        raise ValueError("Simpangan baku noise tidak boleh negatif.")


def _latent_weight_kg(
    age_days: float, birth_weight_kg: float, haz_value: float, coupling: float
) -> float:
    """Heuristik kenaikan berat badan menurut usia.

    BUKAN kurva WHO dan bukan model klinis. Tujuannya hanya menghasilkan
    kolom berat yang berada pada orde besaran yang benar (~3 kg lahir,
    ~8 kg pada 6 bulan, ~10 kg pada 12 bulan, ~13 kg pada 24 bulan) sehingga
    fitur berbasis berat tidak dilatih pada dunia yang rusak secara
    antropometri. Batasan ini wajib dinyatakan di DATA_CARD.
    """
    months = age_days / DAYS_PER_MONTH
    gain = (
        0.80 * min(months, 6.0)
        + 0.40 * float(np.clip(months - 6.0, 0.0, 6.0))
        + 0.20 * float(np.clip(months - 12.0, 0.0, 12.0))
    )
    return max(1.5, birth_weight_kg + gain + coupling * haz_value)


def _child_attributes(rng: np.random.Generator, cfg: SynthConfig, n: int) -> pd.DataFrame:
    ses = rng.normal(0.0, 1.0, n)
    # `care_propensity` dan `exclusive_bf_history` adalah atribut LATEN pembangkit
    # dunia sintetis. Keduanya tidak boleh menjadi kolom yang dilihat model:
    # nilainya merepresentasikan hasil akhir yang belum diketahui pada kunjungan
    # awal, sehingga memakainya sejak usia 0 hari adalah kebocoran waktu.
    return pd.DataFrame({
        "child_id": [f"C{i:05d}" for i in range(n)],
        "sex": rng.choice(["M", "F"], n),
        "ses_index": ses,
        "care_propensity": rng.normal(0.6 * ses, 0.8, n),
        "exclusive_bf_history": rng.random(n) < _sigmoid(0.4 * ses + 0.3),
        "birth_weight_kg": np.clip(rng.normal(3.1 + 0.12 * ses, 0.45, n), 1.5, 5.0),
    })


def _latent_velocity(rng: np.random.Generator, cfg: SynthConfig, attrs: pd.DataFrame) -> np.ndarray:
    n = len(attrs)
    bw_centered = (attrs["birth_weight_kg"].to_numpy() - 3.1) / 0.45
    drift = (
        cfg.w_ses * attrs["ses_index"].to_numpy()
        + cfg.w_immunization * _sigmoid(attrs["care_propensity"].to_numpy())
        + cfg.w_exclusive_bf * attrs["exclusive_bf_history"].to_numpy().astype(float)
        + cfg.w_birth_weight * bw_centered
    )
    return rng.normal(cfg.velocity_mean, cfg.velocity_sd, n) + drift


def generate(cfg: SynthConfig | None = None, *, table: pd.DataFrame | None = None) -> pd.DataFrame:
    """Bangkitkan tabel kunjungan. Deterministik untuk `cfg.seed` yang sama."""
    cfg = cfg or SynthConfig()
    validate_config(cfg)
    rng = np.random.default_rng(cfg.seed)
    tbl = load_table() if table is None else table

    attrs = _child_attributes(rng, cfg, cfg.n_children)
    haz0 = rng.normal(cfg.haz0_mean, cfg.haz0_sd, cfg.n_children)
    vel = _latent_velocity(rng, cfg, attrs)
    has_cp = rng.random(cfg.n_children) < cfg.changepoint_prob
    cp_month = rng.integers(4, 16, cfg.n_children)
    cp_delta = rng.normal(0.0, cfg.changepoint_delta_sd, cfg.n_children)

    start = pd.Timestamp(cfg.start_date)
    rows = []

    for i in range(cfg.n_children):
        a = attrs.iloc[i]
        enroll_offset = (
            0 if cfg.enrollment_window_days == 0
            else int(rng.integers(0, cfg.enrollment_window_days))
        )
        enroll = start + pd.Timedelta(days=enroll_offset)
        birth = enroll - pd.Timedelta(days=int(rng.integers(0, cfg.first_visit_age_days_max + 1)))

        # Peluang hadir: MNAR, dipengaruhi SES.
        p_attend = float(np.clip(
            cfg.base_attendance + cfg.ses_attendance_effect * a["ses_index"] * 0.5,
            0.35, 0.97,
        ))

        age_days = (enroll - birth).days
        visit_date = enroll
        child_rows = []

        while age_days <= MAX_AGE_DAYS:
            if rng.random() < p_attend:
                months = age_days / DAYS_PER_MONTH
                z = haz0[i] + vel[i] * months
                if has_cp[i] and months > cp_month[i]:
                    z += cp_delta[i] * (months - cp_month[i])

                try:
                    true_len = length_from_haz(float(z), a["sex"], float(age_days), tbl)
                except ValueError:
                    break  # z ekstrem di luar domain LMS; hentikan lintasan anak ini

                obs_len = true_len + rng.normal(0.0, cfg.length_noise_sd_cm)
                true_wt = _latent_weight_kg(
                    age_days, float(a["birth_weight_kg"]), float(z), cfg.weight_haz_coupling
                )
                obs_wt = max(1.0, true_wt + rng.normal(0.0, cfg.weight_noise_sd_kg))

                months_now = age_days / DAYS_PER_MONTH
                # "Lengkap SESUAI USIA" pada kunjungan ini -- bukan status final
                # sepanjang hidup anak, yang belum diketahui pada usia dini.
                p_on_schedule = float(_sigmoid(
                    1.0 * a["care_propensity"] + 0.4 * a["ses_index"] - 0.03 * months_now
                ))
                immunization_on_schedule = bool(rng.random() < p_on_schedule)
                # Hasil ASI eksklusif 6 bulan belum dapat diketahui sebelum 180 hari.
                exclusive_bf = (
                    pd.NA if age_days < cfg.exclusive_bf_known_after_days
                    else bool(a["exclusive_bf_history"])
                )

                child_rows.append({
                    "child_id": a["child_id"],
                    "visit_date": visit_date,
                    "birth_date": birth,
                    "age_days": age_days,
                    "sex": a["sex"],
                    "length_cm": np.nan if rng.random() < cfg.missing_length_prob else round(obs_len, 1),
                    "weight_kg": np.nan if rng.random() < cfg.missing_weight_prob else round(obs_wt, 2),
                    "measure_mode": "recumbent",
                    "measured_by_cv": bool(rng.random() < cfg.cv_usage_prob),
                    "immunization_on_schedule": immunization_on_schedule,
                    "exclusive_bf": exclusive_bf,
                    "birth_weight_kg": round(float(a["birth_weight_kg"]), 2),
                    "ses_index": round(float(a["ses_index"]), 4),
                })

            step = cfg.visit_interval_days + int(rng.integers(-cfg.visit_jitter_days, cfg.visit_jitter_days + 1))
            visit_date = visit_date + pd.Timedelta(days=step)
            age_days += step

        if len(child_rows) >= cfg.min_visits:
            rows.extend(child_rows)

    df = pd.DataFrame(rows).sort_values(["child_id", "visit_date"]).reset_index(drop=True)
    df["visit_gap_days"] = (
        df.groupby("child_id")["visit_date"].diff().dt.days
    )
    return df


def summarize(df: pd.DataFrame, haz_col: str = "haz") -> pd.DataFrame:
    """Statistik deskriptif untuk TAB-01. Dilaporkan di paper 4.2 / Lampiran A."""
    stats = {
        "n_children": df["child_id"].nunique(),
        "n_visits": len(df),
        "visits_per_child_mean": round(len(df) / df["child_id"].nunique(), 2),
        "missing_length_pct": round(100 * df["length_cm"].isna().mean(), 2),
        "missing_weight_pct": round(100 * df["weight_kg"].isna().mean(), 2),
        "cv_usage_pct": round(100 * df["measured_by_cv"].mean(), 2),
        "median_gap_days": float(df["visit_gap_days"].median()),
    }
    if haz_col in df.columns:
        z = df[haz_col].dropna()
        stats["haz_mean"] = round(float(z.mean()), 3)
        stats["haz_sd"] = round(float(z.std()), 3)
        # Statistik TINGKAT KUNJUNGAN, bukan estimasi prevalensi populasi anak:
        # anak yang lebih rajin hadir menyumbang lebih banyak baris.
        stats["visits_haz_lt_minus2_pct"] = round(100 * float((z < -2).mean()), 2)
        stats["visits_haz_lt_minus3_pct"] = round(100 * float((z < -3).mean()), 2)
        # groupby.first()/last() MELEWATI NaN, sehingga "kunjungan pertama" bisa
        # diam-diam menjadi kunjungan kedua. Pakai posisi sebenarnya, lalu
        # laporkan coverage agar denominatornya transparan.
        ordered = df.sort_values(["child_id", "visit_date"])
        n_children = df["child_id"].nunique()
        first = ordered.groupby("child_id", sort=False).nth(0)[haz_col].dropna()
        last = ordered.groupby("child_id", sort=False).nth(-1)[haz_col].dropna()
        stats["children_haz_lt_minus2_first_visit_pct"] = round(100 * float((first < -2).mean()), 2)
        stats["children_haz_lt_minus2_last_visit_pct"] = round(100 * float((last < -2).mean()), 2)
        stats["children_first_visit_haz_available_pct"] = round(100 * len(first) / n_children, 2)
        stats["children_last_visit_haz_available_pct"] = round(100 * len(last) / n_children, 2)
    return pd.DataFrame([stats]).T.rename(columns={0: "value"})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-children", type=int, default=SynthConfig.n_children)
    ap.add_argument("--seed", type=int, default=SynthConfig.seed)
    ap.add_argument("--out", type=Path, default=Path("data/synth/posyandu_synth_v1.csv"))
    args = ap.parse_args()

    cfg = SynthConfig(n_children=args.n_children, seed=args.seed)
    df = generate(cfg)

    # HAZ dihitung dari panjang TERUKUR (bernoise), bukan dari lintasan laten --
    # persis seperti yang akan dilihat sistem di lapangan.
    from tabular.who_lms import haz_series
    df["haz"] = haz_series(df)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)

    meta = args.out.with_suffix(".config.json")
    pd.Series(asdict(cfg)).to_json(meta, indent=2)

    print(f"Tersimpan: {args.out}  ({len(df)} kunjungan)")
    print(f"Config    : {meta}")
    print(summarize(df).to_string())


if __name__ == "__main__":
    main()
