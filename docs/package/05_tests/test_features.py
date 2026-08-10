"""Verifikasi feature engineering: bebas kebocoran waktu dan blok dapat diablasi."""

import numpy as np
import pandas as pd
import pytest

from data.generate_synth import SynthConfig, generate
from tabular.features import (
    FEATURE_BLOCKS,
    build_dataset,
    build_features,
    feature_columns,
    missingness_report,
)
from tabular.splits import assert_features_not_future, lint_future_feature_names
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
    df = generate(SynthConfig(n_children=120, seed=5), table=fake_table)
    df["haz"] = haz_series(df, fake_table)
    return df


@pytest.fixture(scope="module")
def feats(cohort):
    return build_features(cohort)


def test_satu_baris_fitur_per_kunjungan(cohort, feats):
    assert len(feats) == len(cohort)
    assert feats.index.equals(cohort.index)


def test_provenance_membuktikan_bebas_kebocoran(feats):
    assert_features_not_future(feats)


def test_nama_kolom_lolos_lint(feats):
    lint_future_feature_names(feature_columns())


def test_max_source_date_tidak_pernah_melewati_tanggal_prediksi(feats):
    assert (feats["max_source_date"] <= feats["prediction_date"]).all()


def test_fitur_lintasan_kosong_pada_kunjungan_pertama(feats):
    first = feats[feats["visit_index"] == 0]
    assert first["visit_gap_days_t"].isna().all()
    assert first["haz_delta_1visit"].isna().all()
    assert (first["n_prior_visits"] == 0).all()


def test_kunjungan_pertama_tetap_dipertahankan(cohort, feats):
    assert (feats["visit_index"] == 0).sum() == cohort["child_id"].nunique()


def test_semua_blok_terwakili(feats):
    for cols in FEATURE_BLOCKS.values():
        assert set(cols).issubset(feats.columns)


def test_ablasi_menghasilkan_subset_kolom(cohort):
    snap = build_dataset(cohort, ["snapshot"])
    full = build_dataset(cohort, ["snapshot", "trajectory", "contextual"])
    assert set(snap.columns).issubset(full.columns)
    assert len(full.columns) > len(snap.columns)


def test_blok_tidak_dikenal_ditolak():
    with pytest.raises(ValueError, match="Blok tidak dikenal"):
        feature_columns(["snapshot", "magic"])


def test_slope_positif_pada_lintasan_membaik(fake_table):
    df = pd.DataFrame({
        "child_id": ["A"] * 4,
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]),
        "age_days": [100, 131, 159, 190],
        "sex": ["M"] * 4,
        "length_cm": [60.0, 62.0, 64.0, 66.0],
        "haz": [-2.5, -2.2, -1.9, -1.5],
    })
    f = build_features(df)
    assert f["haz_slope_per_month"].iloc[-1] > 0
    assert f["haz_delta_1visit"].iloc[-1] == pytest.approx(0.4)
    assert f["n_consecutive_declines"].iloc[-1] == 0


def test_penurunan_berturut_turut_terhitung(fake_table):
    df = pd.DataFrame({
        "child_id": ["A"] * 4,
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"]),
        "age_days": [100, 131, 159, 190],
        "sex": ["M"] * 4,
        "length_cm": [60.0, 61.0, 61.5, 62.0],
        "haz": [-1.0, -1.4, -1.9, -2.3],
    })
    f = build_features(df)
    assert f["n_consecutive_declines"].iloc[-1] == 3
    assert f["ever_stunted_to_date"].iloc[-1] == 1.0
    assert f["haz_min_to_date"].iloc[-1] == pytest.approx(-2.3)


def test_delta_tiga_bulan_memakai_pengamatan_dalam_jendela():
    df = pd.DataFrame({
        "child_id": ["A"] * 3,
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-04-02"]),
        "age_days": [100, 131, 191],
        "sex": ["M"] * 3,
        "length_cm": [60.0, 61.0, 63.0],
        "haz": [-1.0, -1.2, -1.8],
    })
    f = build_features(df)
    # 91 hari dari baris pertama -> delta terhadap -1.0
    assert f["haz_delta_3months"].iloc[-1] == pytest.approx(-0.8)


def test_haz_kosong_ditandai_bukan_dibuang():
    df = pd.DataFrame({
        "child_id": ["A"] * 3,
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]),
        "age_days": [100, 131, 159],
        "sex": ["M"] * 3,
        "length_cm": [60.0, np.nan, 64.0],
        "haz": [-1.0, np.nan, -1.6],
    })
    f = build_features(df)
    assert len(f) == 3
    assert f["haz_missing_t"].tolist() == [0.0, 1.0, 0.0]
    # delta memakai pengamatan tersedia sebelumnya, bukan baris kosong
    assert f["haz_delta_1visit"].iloc[-1] == pytest.approx(-0.6)


def test_exclusive_bf_belum_diketahui_dipisah_dari_negatif(cohort, feats):
    early = feats[feats["age_days"] < 180]
    assert (early["exclusive_bf_known"] == 0.0).all()
    assert (early["exclusive_bf_positive"] == 0.0).all()
    late = feats[feats["age_days"] >= 180]
    assert (late["exclusive_bf_known"] == 1.0).all()


def test_index_tidak_unik_ditolak(cohort):
    bad = cohort.copy()
    bad.index = [0] * len(bad)
    with pytest.raises(ValueError, match="unik"):
        build_features(bad)


def test_kolom_wajib_divalidasi():
    with pytest.raises(ValueError, match="Kolom hilang"):
        build_features(pd.DataFrame({"child_id": ["A"]}))


def test_missingness_report_mencakup_semua_fitur(feats):
    rep = missingness_report(feats)
    assert set(rep["feature"]) == set(feature_columns())
    assert rep["missing_pct"].between(0, 100).all()
