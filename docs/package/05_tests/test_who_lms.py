"""Verifikasi konversi HAZ (DEC-009).

Dua lapis pengujian:

A.  **Invarian matematis** -- berjalan tanpa tabel WHO, memakai tabel sintetis.
    Menangkap kesalahan rumus, inverse, dan validasi rentang.

B.  **Kasus rujukan resmi WHO** -- berjalan hanya bila `data/who/lhfa_lms.csv`
    dan `tests/who_reference_cases.csv` sudah ada. INI YANG SEBENARNYA
    MEMENUHI DEC-009. Lapis A saja tidak cukup: rumus benar dengan tabel salah
    tetap menghasilkan angka salah.

Cara mengisi lapis B: ambil beberapa baris dari tabel z-score WHO (nilai panjang
badan pada Z = -3, -2, 0, +2 untuk beberapa usia dan kedua jenis kelamin) lalu
tulis ke `tests/who_reference_cases.csv` dengan kolom:

    sex,age_days,length_cm,expected_haz
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tabular.who_lms import (
    MAX_AGE_DAYS,  # noqa: F401  (dipakai di test cakupan tabel)
    AgeOutOfRangeError,
    classify,
    haz,
    haz_series,
    length_from_haz,
)

ROOT = Path(__file__).resolve().parents[1]
WHO_TABLE = ROOT / "data" / "who" / "lhfa_lms.csv"
REF_CASES = Path(__file__).resolve().parent / "who_reference_cases.csv"


@pytest.fixture
def fake_table():
    """Tabel LMS sintetis. BUKAN nilai WHO -- hanya untuk menguji rumus."""
    rows = []
    for sex, m0, growth in (("M", 49.9, 0.030), ("F", 49.1, 0.029)):
        for age in range(0, MAX_AGE_DAYS + 1, 10):
            rows.append({
                "sex": sex,
                "age_days": age,
                "L": 1.0,
                "M": m0 + growth * age,
                "S": 0.038 + 0.000002 * age,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- lapis A

def test_panjang_sama_dengan_median_menghasilkan_z_nol(fake_table):
    from tabular.who_lms import get_lms
    p = get_lms("M", 200, fake_table)
    assert haz(p.M, "M", 200, fake_table) == pytest.approx(0.0, abs=1e-12)


def test_l_sama_dengan_satu_menyederhana_ke_bentuk_linear(fake_table):
    from tabular.who_lms import get_lms
    p = get_lms("F", 365, fake_table)
    x = p.M * 0.94
    assert haz(x, "F", 365, fake_table) == pytest.approx((x - p.M) / (p.M * p.S), rel=1e-12)


def test_inverse_konsisten_bolak_balik(fake_table):
    for z in (-3.5, -2.0, -0.5, 0.0, 1.7):
        cm = length_from_haz(z, "M", 400, fake_table)
        assert haz(cm, "M", 400, fake_table) == pytest.approx(z, abs=1e-9)


def test_haz_monoton_naik_terhadap_panjang(fake_table):
    zs = [haz(cm, "M", 300, fake_table) for cm in (55, 60, 65, 70, 75)]
    assert all(np.diff(zs) > 0)


def test_haz_turun_bila_usia_bertambah_pada_panjang_tetap(fake_table):
    assert haz(70, "M", 200, fake_table) > haz(70, "M", 500, fake_table)


def test_tidak_ada_penyesuaian_ekor_untuk_haz(fake_table):
    """HAZ tidak dikoreksi pada |Z| > 3 -- itu hanya untuk indikator berat."""
    from tabular.who_lms import get_lms
    p = get_lms("M", 300, fake_table)
    x = p.M * (1 + p.S * -4.0)
    assert haz(x, "M", 300, fake_table) == pytest.approx(-4.0, abs=1e-9)


@pytest.mark.parametrize("age", [-1, MAX_AGE_DAYS + 1, 5000, float("nan")])
def test_usia_di_luar_rentang_mvp_ditolak(fake_table, age):
    with pytest.raises(AgeOutOfRangeError):
        haz(70, "M", age, fake_table)


def test_batas_rentang_diterima(fake_table):
    assert np.isfinite(haz(50, "M", 0, fake_table))
    assert np.isfinite(haz(85, "M", MAX_AGE_DAYS, fake_table))


@pytest.mark.parametrize("bad", [0, -5, float("nan"), float("inf")])
def test_panjang_tidak_valid_ditolak(fake_table, bad):
    with pytest.raises(ValueError):
        haz(bad, "M", 200, fake_table)


def test_jenis_kelamin_tidak_dikenal_ditolak(fake_table):
    with pytest.raises(ValueError):
        haz(70, "X", 200, fake_table)


@pytest.mark.parametrize("z,expected", [
    (-3.01, "severely_stunted"),
    (-3.00, "stunted"),
    (-2.01, "stunted"),
    (-2.00, "normal"),
    (0.0, "normal"),
])
def test_ambang_klasifikasi_who(z, expected):
    assert classify(z) == expected


def test_haz_series_memberi_nan_bukan_membuang_baris(fake_table):
    df = pd.DataFrame({
        "sex": ["M", "M", "F"],
        "age_days": [200, 9999, 300],  # baris tengah di luar rentang
        "length_cm": [70.0, 70.0, 72.0],
    })
    out = haz_series(df, fake_table)
    assert len(out) == 3
    assert np.isnan(out.iloc[1])
    assert out.notna().sum() == 2


# ---------------------------------------------------------------- lapis B

@pytest.mark.skipif(not WHO_TABLE.exists(), reason="Tabel WHO belum disiapkan.")
def test_tabel_who_mencakup_seluruh_rentang_mvp():
    """Tabel bulanan WHO berakhir di bulan 24 = 730.5 hari.

    Tanpa baris anchor tersebut, preprocessing terpotong di bulan 23
    (700.06 hari) dan usia 701-730 hari tidak dapat diinterpolasi -- padahal
    who_lms menyatakan mendukung sampai 730 hari.
    """
    from tabular.who_lms import load_table
    coverage = load_table(WHO_TABLE).groupby("sex")["age_days"].max()
    assert set(coverage.index) == {"M", "F"}
    assert (coverage >= MAX_AGE_DAYS).all(), (
        f"Cakupan usia kurang: {coverage.to_dict()}. Jalankan ulang "
        "scripts/prepare_who_tables.py versi terbaru (anchor bulan 24)."
    )


@pytest.mark.skipif(not WHO_TABLE.exists(), reason="Tabel WHO belum disiapkan.")
def test_batas_atas_rentang_mvp_dapat_dihitung():
    from tabular.who_lms import load_table
    tbl = load_table(WHO_TABLE)
    for sex in ("M", "F"):
        assert np.isfinite(haz(85.0, sex, MAX_AGE_DAYS, tbl))


@pytest.mark.skipif(
    not (WHO_TABLE.exists() and REF_CASES.exists()),
    reason="Tabel WHO atau kasus rujukan belum disiapkan (DEC-009 belum terpenuhi).",
)
def test_cocok_dengan_kasus_rujukan_who():
    from tabular.who_lms import load_table
    tbl = load_table(WHO_TABLE)
    cases = pd.read_csv(REF_CASES, comment="#")

    required = {"sex", "age_days", "length_cm", "expected_haz"}
    missing = required - set(cases.columns)
    assert not missing, f"Kolom rujukan WHO hilang: {sorted(missing)}"
    assert len(cases) >= 8, (
        f"DEC-009 memerlukan minimal 8 kasus rujukan WHO; ditemukan {len(cases)}. "
        "File yang hanya berisi header akan membuat test ini lulus tanpa menguji apa pun."
    )

    # Toleransi bergantung sumber rujukan:
    #   0.01 -> keluaran WHO Anthro (presisi penuh)
    #   0.05 -> tabel z-score WHO yang panjangnya dibulatkan 1 desimal;
    #           pembulatan itu sendiri menggeser Z ~0.012-0.016
    # Kolom `tol` opsional per baris; default 0.05 (asumsi paling aman).
    errors = []
    for i, r in cases.iterrows():
        if "tol" in cases.columns:
            tol = 0.05 if pd.isna(r["tol"]) else float(r["tol"])
        else:
            tol = 0.05
        # tol NaN akan membuat `error > tol` selalu False -> kasus salah lolos.
        assert np.isfinite(tol) and tol > 0, f"Toleransi tidak valid pada baris {i}: {tol}"
        got = haz(float(r.length_cm), r.sex, float(r.age_days), tbl)
        if abs(got - float(r.expected_haz)) > tol:
            errors.append(
                f"sex={r.sex} age={r.age_days}d len={r.length_cm}cm: "
                f"harap {r.expected_haz} (tol {tol}), dapat {got:.4f}"
            )
    assert not errors, "Selisih terhadap rujukan WHO:\n" + "\n".join(errors)


def test_dec009_belum_terpenuhi_bila_rujukan_belum_ada():
    """Pengingat eksplisit, bukan kegagalan.

    Selama file rujukan belum ada, DEC-009 belum terpenuhi dan angka HAZ belum
    boleh dianggap terverifikasi di paper.
    """
    if not REF_CASES.exists():
        pytest.skip(
            "tests/who_reference_cases.csv belum ada -> DEC-009 BELUM terpenuhi. "
            "Isi minimal 8 kasus dari tabel z-score WHO sebelum angka HAZ dipakai."
        )


def test_sex_string_kosong_menghasilkan_valueerror_bukan_indexerror(fake_table):
    for bad in ("", "   ", None, 123):
        with pytest.raises(ValueError):
            haz(70.0, bad, 200, fake_table)


def test_sex_alias_indonesia_dan_inggris_diterima(fake_table):
    ref = haz(70.0, "M", 200, fake_table)
    for alias in ("m", " M ", "male", "L", "laki-laki"):
        assert haz(70.0, alias, 200, fake_table) == pytest.approx(ref)
    ref_f = haz(70.0, "F", 200, fake_table)
    for alias in ("f", "female", "P", "perempuan"):
        assert haz(70.0, alias, 200, fake_table) == pytest.approx(ref_f)


def test_inverse_lms_menolak_z_di_luar_domain(fake_table):
    with pytest.raises(ValueError, match="domain inverse LMS"):
        length_from_haz(-40.0, "M", 300, fake_table)


def test_inverse_lms_tidak_pernah_mengembalikan_panjang_negatif(fake_table):
    for z in (-3.0, -2.0, 0.0, 3.0):
        assert length_from_haz(z, "F", 400, fake_table) > 0


def test_haz_series_tidak_crash_pada_sex_rusak(fake_table):
    df = pd.DataFrame({
        "sex": ["M", "", "F"],
        "age_days": [200, 200, 300],
        "length_cm": [70.0, 70.0, 72.0],
    })
    out = haz_series(df, fake_table)
    assert len(out) == 3 and np.isnan(out.iloc[1]) and out.notna().sum() == 2
