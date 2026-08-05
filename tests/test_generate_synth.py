"""Verifikasi properti kohort sintetis (TAB-01).

Test ini menjaga tiga hal yang menentukan sah-tidaknya eksperimen hilir:
label tidak deterministik dari fitur, ketidakhadiran bersifat MNAR, dan
generator reprodusibel.
"""

import numpy as np
import pandas as pd
import pytest

from data.generate_synth import SynthConfig, generate, summarize
from tabular.target import attach_labels, drop_report
from tabular.who_lms import MAX_AGE_DAYS, haz_series


@pytest.fixture(scope="module")
def fake_table():
    rows = []
    for sex, m0 in (("M", 49.9), ("F", 49.1)):
        for age in range(0, MAX_AGE_DAYS + 31, 10):
            rows.append({"sex": sex, "age_days": age, "L": 1.0,
                         "M": m0 + 0.0305 * age, "S": 0.038 + 0.000002 * age})
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def cohort(fake_table):
    df = generate(SynthConfig(n_children=300, seed=1), table=fake_table)
    df["haz"] = haz_series(df, fake_table)
    return df


def test_deterministik_dengan_seed_sama(fake_table):
    a = generate(SynthConfig(n_children=40, seed=7), table=fake_table)
    b = generate(SynthConfig(n_children=40, seed=7), table=fake_table)
    pd.testing.assert_frame_equal(a, b)


def test_seed_berbeda_menghasilkan_kohort_berbeda(fake_table):
    a = generate(SynthConfig(n_children=40, seed=1), table=fake_table)
    b = generate(SynthConfig(n_children=40, seed=2), table=fake_table)
    assert not a.equals(b)


def test_usia_selalu_dalam_rentang_mvp(cohort):
    assert cohort["age_days"].min() >= 0
    assert cohort["age_days"].max() <= MAX_AGE_DAYS


def test_kunjungan_terurut_dan_usia_bertambah(cohort):
    for _, g in cohort.groupby("child_id"):
        assert g["visit_date"].is_monotonic_increasing
        assert (g["age_days"].diff().dropna() > 0).all()


def test_setiap_anak_punya_minimal_dua_kunjungan(cohort):
    assert cohort.groupby("child_id").size().min() >= 2


def test_atribut_tetap_konsisten_antar_kunjungan(cohort):
    """Hanya atribut yang memang tidak berubah sepanjang hidup anak."""
    for col in ("sex", "ses_index", "birth_weight_kg"):
        assert (cohort.groupby("child_id")[col].nunique() == 1).all()


def test_status_imunisasi_bervariasi_antar_kunjungan(cohort):
    """`immunization_on_schedule` adalah status PADA kunjungan itu.

    Kalau konstan sepanjang hidup anak, kolom itu membocorkan hasil akhir yang
    belum diketahui pada kunjungan awal.
    """
    varies = cohort.groupby("child_id")["immunization_on_schedule"].nunique()
    assert (varies > 1).mean() > 0.5, "status imunisasi tidak berubah antar kunjungan"


def test_exclusive_bf_belum_diketahui_sebelum_180_hari(cohort):
    early = cohort[cohort["age_days"] < 180]["exclusive_bf"]
    late = cohort[cohort["age_days"] >= 180]["exclusive_bf"]
    assert early.isna().all(), "status ASI eksklusif tidak boleh terisi sebelum 180 hari"
    assert late.notna().all()


def test_berat_badan_berada_pada_orde_yang_benar(cohort):
    def med(lo, hi):
        m = cohort[(cohort.age_days >= lo) & (cohort.age_days < hi)]["weight_kg"].median()
        return float(m)

    assert 2.0 < med(0, 31) < 5.5, f"berat neonatus tidak wajar: {med(0, 31):.2f} kg"
    assert 5.5 < med(150, 210) < 10.5, f"berat 6 bulan tidak wajar: {med(150, 210):.2f} kg"
    assert 7.5 < med(330, 400) < 13.0, f"berat 12 bulan tidak wajar: {med(330, 400):.2f} kg"
    assert 9.0 < med(690, 731) < 17.0, f"berat 24 bulan tidak wajar: {med(690, 731):.2f} kg"
    assert cohort["weight_kg"].max() < 22.0


def test_berat_naik_seiring_usia(cohort):
    by_age = cohort.groupby(pd.cut(cohort.age_days, [0, 90, 180, 365, 730], right=False),
                            observed=True)["weight_kg"].median()
    assert by_age.is_monotonic_increasing


@pytest.mark.parametrize("kwargs", [
    {"n_children": 0},
    {"min_visits": 1},
    {"visit_interval_days": 5, "visit_jitter_days": 10},
    {"base_attendance": 1.5},
    {"cv_usage_prob": -0.1},
    {"first_visit_age_days_max": -3},
])
def test_config_tidak_valid_ditolak(kwargs):
    with pytest.raises(ValueError):
        generate(SynthConfig(**kwargs))


def test_ada_data_hilang_pada_panjang_dan_berat(cohort):
    assert 0 < cohort["length_cm"].isna().mean() < 0.2
    assert 0 < cohort["weight_kg"].isna().mean() < 0.2


def test_ketidakhadiran_bersifat_mnar(cohort):
    """Anak ber-SES rendah harus punya kunjungan lebih sedikit."""
    per_child = cohort.groupby("child_id").agg(n=("visit_date", "size"), ses=("ses_index", "first"))
    lo = per_child[per_child.ses < per_child.ses.quantile(0.25)]["n"].mean()
    hi = per_child[per_child.ses > per_child.ses.quantile(0.75)]["n"].mean()
    assert lo < hi, f"MNAR tidak terbentuk: SES rendah {lo:.2f} vs SES tinggi {hi:.2f}"


def test_prevalensi_stunting_masuk_akal(cohort):
    pct = float((cohort["haz"].dropna() < -2).mean())
    assert 0.05 < pct < 0.50, f"prevalensi stunting {pct:.1%} di luar rentang wajar"


def test_label_tidak_deterministik_dari_haz_terkini(cohort):
    """Anti-sirkularitas: HAZ terkini TIDAK boleh menentukan label secara pasti.

    Kalau setiap nilai HAZ memetakan ke satu label, model hanya akan menghafal
    aturan generator dan seluruh angka di paper tidak bermakna (DEC-007).
    """
    lab = attach_labels(cohort).dropna(subset=["y_deterioration"])
    bins = pd.cut(lab["haz"], bins=[-6, -3, -2, -1, 0, 6])
    rates = lab.groupby(bins, observed=True)["y_deterioration"].mean()
    assert (rates > 0).any() and (rates < 1).any()
    assert ((rates > 0.02) & (rates < 0.98)).sum() >= 2, (
        f"label terlalu deterministik terhadap HAZ terkini:\n{rates}"
    )


def test_kedua_kelas_label_terbentuk(cohort):
    lab = attach_labels(cohort)["y_deterioration"].dropna()
    assert lab.nunique() == 2
    rate = float(lab.mean())
    assert 0.02 < rate < 0.60, f"prevalensi deteriorasi {rate:.1%} tidak wajar"


def test_baris_yang_dibuang_terlacak_alasannya(cohort):
    lab = attach_labels(cohort)
    rep = drop_report(lab)
    # `n` harus persis; `pct` dibulatkan 2 desimal sehingga boleh meleset tipis.
    assert rep["n"].sum() == len(lab)
    assert abs(rep["pct"].sum() - 100.0) < 0.5
    assert rep.loc[rep["reason"] == "kept", "n"].iloc[0] > 0


def test_summarize_menghasilkan_metrik_yang_dilaporkan(cohort):
    s = summarize(cohort)
    for key in ("n_children", "n_visits", "missing_length_pct",
                "visits_haz_lt_minus2_pct",
                "children_haz_lt_minus2_first_visit_pct",
                "children_haz_lt_minus2_last_visit_pct"):
        assert key in s.index


def test_cutoff_asi_negatif_ditolak():
    """Cutoff negatif akan membuka kembali kebocoran waktu yang sudah ditutup."""
    with pytest.raises(ValueError, match="exclusive_bf_known_after_days"):
        generate(SynthConfig(n_children=3, exclusive_bf_known_after_days=-1))


def test_cutoff_asi_di_luar_rentang_usia_ditolak():
    with pytest.raises(ValueError, match="exclusive_bf_known_after_days"):
        generate(SynthConfig(n_children=3, exclusive_bf_known_after_days=MAX_AGE_DAYS + 1))


@pytest.mark.parametrize("kwargs", [
    {"visit_jitter_days": -1},
    {"enrollment_window_days": -5},
])
def test_parameter_jadwal_negatif_ditolak(kwargs):
    with pytest.raises(ValueError):
        generate(SynthConfig(n_children=3, **kwargs))


def test_enrollment_window_nol_tidak_crash(fake_table):
    df = generate(SynthConfig(n_children=5, enrollment_window_days=0, seed=3),
                  table=fake_table)
    assert len(df) > 0


def test_statistik_first_visit_memakai_kunjungan_sebenarnya(fake_table):
    """groupby.first() melewati NaN; posisi sebenarnya tidak boleh bergeser."""
    df = pd.DataFrame({
        "child_id": ["A", "A", "B", "B"],
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01",
                                      "2025-01-01", "2025-02-01"]),
        "age_days": [100, 131, 100, 131],
        "length_cm": [70.0, 71.0, 70.0, 71.0],
        "weight_kg": [8.0, 8.4, 8.0, 8.4],
        "measured_by_cv": [True] * 4,
        "visit_gap_days": [np.nan, 31, np.nan, 31],
        "haz": [np.nan, -3.0, -1.0, -1.0],  # A: kunjungan pertama HAZ kosong
    })
    s = summarize(df)
    # Hanya B yang punya HAZ pada kunjungan pertama, dan B tidak stunted.
    assert float(s.loc["children_haz_lt_minus2_first_visit_pct", "value"]) == 0.0
    assert float(s.loc["children_first_visit_haz_available_pct", "value"]) == 50.0
