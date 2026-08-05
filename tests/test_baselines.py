"""Verifikasi baseline ranking (DEC-012)."""

import numpy as np
import pandas as pd
import pytest

from tabular.baselines import (
    B1Model,
    b0_haz_only,
    fit_b1,
    make_b2,
    rule_stunted_now,
)
from tabular.evaluate import recall_at_k


@pytest.fixture
def X():
    rng = np.random.default_rng(0)
    n = 400
    return pd.DataFrame({
        "haz_t": rng.normal(-1.0, 1.2, n),
        "haz_slope_per_month": rng.normal(-0.02, 0.05, n),
        "age_days": rng.integers(30, 700, n).astype(float),
    })


def test_b0_memberi_prioritas_tinggi_pada_haz_rendah():
    X = pd.DataFrame({"haz_t": [-3.0, -1.0, 0.5]})
    s = b0_haz_only(X)
    assert s[0] > s[1] > s[2]


def test_b0_menghasilkan_skor_kontinu_bukan_biner(X):
    s = b0_haz_only(X)
    assert len(np.unique(s)) > 2, "B0 harus dapat mengurutkan, bukan hanya 0/1"


def test_b0_menangani_haz_kosong():
    X = pd.DataFrame({"haz_t": [-3.0, np.nan, 0.5]})
    s = b0_haz_only(X)
    assert np.isfinite(s).all()
    assert s[1] == s.min(), "haz_t kosong -> prioritas terendah, bukan median batch"


def test_b0_butuh_kolom_haz():
    with pytest.raises(ValueError, match="haz_t"):
        b0_haz_only(pd.DataFrame({"age_days": [100.0]}))


def test_bobot_b1_dipilih_dari_validation(X):
    rng = np.random.default_rng(1)
    y = (rng.random(len(X)) < 0.2).astype(float)
    m = fit_b1(X, X, y)
    assert isinstance(m, B1Model)
    assert m.w_haz + m.w_slope == pytest.approx(1.0, abs=1e-6)


def test_b1_memakai_slope_bila_slope_informatif():
    """Kalau label hanya ditentukan slope, B1 harus memberi bobot ke slope."""
    n = 400
    rng = np.random.default_rng(2)
    slope = rng.normal(0, 0.05, n)
    X = pd.DataFrame({"haz_t": rng.normal(-1, 1, n), "haz_slope_per_month": slope})
    y = (slope < np.quantile(slope, 0.2)).astype(float)
    m = fit_b1(X, X, y)
    assert m.w_slope > m.w_haz


def test_b1_memakai_haz_bila_haz_informatif():
    n = 400
    rng = np.random.default_rng(3)
    haz = rng.normal(-1, 1, n)
    X = pd.DataFrame({"haz_t": haz, "haz_slope_per_month": rng.normal(0, 0.05, n)})
    y = (haz < np.quantile(haz, 0.2)).astype(float)
    m = fit_b1(X, X, y)
    assert m.w_haz > m.w_slope


def test_b1_butuh_kolom_slope(X):
    with pytest.raises(ValueError, match="haz_slope_per_month"):
        fit_b1(X[["haz_t"]], X[["haz_t"]], np.zeros(len(X)))


def test_b1_menghasilkan_skor_kontinu(X):
    m = fit_b1(X, X, np.zeros(len(X)))
    s = m.predict(X)
    assert len(np.unique(s)) > 2 and np.isfinite(s).all()


def test_aturan_biner_hanya_menghasilkan_nol_satu():
    X = pd.DataFrame({"haz_t": [-3.0, -2.5, -1.9, np.nan]})
    r = rule_stunted_now(X)
    assert set(np.unique(r)).issubset({0.0, 1.0})
    assert r.tolist() == [1.0, 1.0, 0.0, 0.0]


def test_aturan_biner_tidak_dapat_mengurutkan(X):
    """Inilah alasan B0 tidak boleh berupa aturan biner (DEC-012)."""
    r = rule_stunted_now(X)
    assert len(np.unique(r)) <= 2


def test_b2_dapat_dilatih_dan_memberi_probabilitas(X):
    rng = np.random.default_rng(4)
    y = (X["haz_t"] + rng.normal(0, 0.5, len(X)) < -1.5).astype(int)
    m = make_b2()
    m.fit(X, y)
    p = m.predict_proba(X)[:, 1]
    assert ((p >= 0) & (p <= 1)).all()
    assert recall_at_k(y, p, 0.2) > 0.2, "B2 harus lebih baik daripada acak"


def test_b2_menangani_nilai_kosong(X):
    Xn = X.copy()
    Xn.loc[Xn.index[:20], "haz_t"] = np.nan
    y = (Xn["haz_t"].fillna(0) < -1).astype(int)
    m = make_b2()
    m.fit(Xn, y)
    assert np.isfinite(m.predict_proba(Xn)[:, 1]).all()
