"""Verifikasi split bebas kebocoran (DEC-003 / TAB-03).

Test ini adalah bukti untuk klaim C-B4 di CLAIMS_MATRIX. Kalau gagal, seluruh
angka model tidak boleh masuk paper.
"""

import numpy as np
import pandas as pd
import pytest

from tabular.splits import (
    assert_features_not_future,
    assert_no_child_leakage,
    grouped_split,
    lint_future_feature_names,
    temporal_split,
)


@pytest.fixture
def cohort():
    rng = np.random.default_rng(0)
    rows = []
    for c in range(50):
        start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 120)))
        for v in range(int(rng.integers(3, 9))):
            rows.append({
                "child_id": f"C{c:03d}",
                "visit_date": start + pd.Timedelta(days=30 * v),
                "haz": float(rng.normal(-1, 1)),
            })
    return pd.DataFrame(rows)


def test_grouped_split_tidak_membocorkan_anak(cohort):
    assert_no_child_leakage(grouped_split(cohort, seed=42))


def test_grouped_split_mencakup_semua_baris(cohort):
    s = grouped_split(cohort, seed=42)
    total = len(s.train) + len(s.val) + len(s.test)
    assert total == len(cohort)
    assert len(set(s.train) & set(s.test)) == 0


def test_grouped_split_deterministik_dengan_seed_sama(cohort):
    a = grouped_split(cohort, seed=7)
    b = grouped_split(cohort, seed=7)
    assert a.child_ids == b.child_ids


def test_seed_berbeda_menghasilkan_partisi_berbeda(cohort):
    a = grouped_split(cohort, seed=1)
    b = grouped_split(cohort, seed=2)
    assert a.child_ids != b.child_ids


def test_setiap_anak_hanya_di_satu_split(cohort):
    s = grouped_split(cohort, seed=42)
    for name, idx in (("train", s.train), ("val", s.val), ("test", s.test)):
        children = set(cohort.loc[idx, "child_id"])
        assert children == set(s.child_ids[name])


def test_temporal_split_test_selalu_setelah_train(cohort):
    s = temporal_split(cohort, test_frac=0.2, seed=42)
    d = cohort.copy()
    d["visit_date"] = pd.to_datetime(d["visit_date"])
    assert d.loc[s.test, "visit_date"].min() >= d.loc[s.train, "visit_date"].max()


def test_temporal_split_val_tidak_bocor_ke_train(cohort):
    s = temporal_split(cohort, test_frac=0.2, seed=42)
    assert set(s.child_ids["train"]).isdisjoint(set(s.child_ids["val"]))


def test_temporal_split_mencakup_semua_baris(cohort):
    s = temporal_split(cohort, test_frac=0.2, seed=42)
    assert len(s.train) + len(s.val) + len(s.test) == len(cohort)


def test_fraksi_tidak_valid_ditolak(cohort):
    with pytest.raises(ValueError):
        grouped_split(cohort, train_frac=0.9, val_frac=0.2)


def test_nama_kolom_masa_depan_ditolak():
    with pytest.raises(AssertionError, match="masa depan"):
        lint_future_feature_names(["haz_t", "haz_next"])


def test_nama_kolom_wajar_diterima():
    lint_future_feature_names(["haz_t", "haz_slope_3m", "age_days"])


def test_fitur_memakai_data_masa_depan_ditolak():
    feats = pd.DataFrame({
        "prediction_date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
        "max_source_date": pd.to_datetime(["2025-01-01", "2025-03-01"]),
    })
    with pytest.raises(AssertionError, match="setelah tanggal prediksi"):
        assert_features_not_future(feats)


def test_fitur_hanya_memakai_data_lampau_diterima():
    feats = pd.DataFrame({
        "prediction_date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
        "max_source_date": pd.to_datetime(["2024-12-01", "2025-02-01"]),
    })
    assert_features_not_future(feats)


def test_kolom_provenance_wajib_ada():
    with pytest.raises(ValueError, match="provenance"):
        assert_features_not_future(pd.DataFrame({"prediction_date": []}))


def test_index_tidak_unik_ditolak(cohort):
    bad = pd.concat([cohort, cohort])
    with pytest.raises(ValueError, match="unik"):
        grouped_split(bad)


def test_child_id_kosong_ditolak(cohort):
    bad = cohort.copy()
    bad.loc[bad.index[0], "child_id"] = None
    with pytest.raises(ValueError, match="child_id"):
        grouped_split(bad)


def test_dataframe_kosong_ditolak():
    with pytest.raises(ValueError, match="kosong"):
        grouped_split(pd.DataFrame({"child_id": [], "visit_date": []}))


def test_split_kosong_ditolak():
    tiny = pd.DataFrame({
        "child_id": ["A", "A", "B"],
        "visit_date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-01"]),
    })
    with pytest.raises(ValueError, match="kosong"):
        grouped_split(tiny, train_frac=0.9, val_frac=0.05, seed=1)


def test_prediction_date_kosong_ditolak():
    feats = pd.DataFrame({
        "prediction_date": [pd.NaT, pd.Timestamp("2025-02-01")],
        "max_source_date": pd.to_datetime(["2099-01-01", "2025-01-01"]),
    })
    with pytest.raises(ValueError, match="tidak boleh kosong"):
        assert_features_not_future(feats)


def test_max_source_date_kosong_ditolak():
    feats = pd.DataFrame({
        "prediction_date": pd.to_datetime(["2025-01-01", "2025-02-01"]),
        "max_source_date": [pd.NaT, pd.Timestamp("2025-01-01")],
    })
    with pytest.raises(ValueError, match="tidak boleh kosong"):
        assert_features_not_future(feats)


def test_child_id_string_kosong_ditolak_pada_split(cohort):
    bad = cohort.copy()
    bad.loc[bad.index[0], "child_id"] = "   "
    with pytest.raises(ValueError, match="child_id"):
        grouped_split(bad)
