"""Verifikasi atribusi SHAP (TAB-09)."""

import numpy as np
import pandas as pd
import pytest

from tabular.explain import (
    DISCLAIMER,
    Explainer,
    FEATURE_LABELS,
    label_for,
    to_sentences,
)
from tabular.features import feature_columns


@pytest.fixture(scope="module")
def fitted():
    import lightgbm as lgb

    rng = np.random.default_rng(0)
    n = 600
    slope = rng.normal(-0.02, 0.05, n)
    haz = rng.normal(-1.0, 1.2, n)
    noise = rng.normal(0, 0.3, n)
    X = pd.DataFrame({
        "haz_t": haz,
        "haz_slope_per_month": slope,
        "age_days": rng.integers(30, 700, n).astype(float),
        "ses_index": rng.normal(0, 1, n),
    })
    # Label didominasi slope. Bobotnya disetel agar kontribusi slope benar-benar
    # jauh lebih besar: sd(slope)=0.05 sedangkan sd(haz)=1.2, jadi koefisien
    # harus mengimbangi skala -- kalau tidak, `haz` justru yang dominan dan
    # ekspektasi test-nya yang salah, bukan kodenya.
    y = ((-30 * slope + 0.05 * haz + 0.3 * noise) > 0.5).astype(int)
    model = lgb.LGBMClassifier(n_estimators=80, num_leaves=15, verbose=-1, random_state=0)
    model.fit(X, y)
    return Explainer(model, list(X.columns)), X, y


def test_setiap_fitur_punya_label_terbaca(fitted):
    for col in feature_columns():
        assert col in FEATURE_LABELS, f"{col} belum punya label untuk UI"
        assert FEATURE_LABELS[col] != col


def test_label_tidak_dikenal_dikembalikan_apa_adanya():
    assert label_for("kolom_baru") == "kolom_baru"


def test_shap_menghasilkan_satu_nilai_per_fitur(fitted):
    ex, X, _ = fitted
    vals = ex.shap_values(X.head(10))
    assert vals.shape == (10, len(ex.feature_names))
    assert np.isfinite(vals).all()


def test_kolom_fitur_hilang_ditolak(fitted):
    ex, X, _ = fitted
    with pytest.raises(ValueError, match="Kolom fitur hilang"):
        ex.shap_values(X.drop(columns=["haz_t"]).head(5))


def test_faktor_teratas_terurut_berdasarkan_besaran(fitted):
    ex, X, _ = fitted
    attrs = ex.explain_child(X, X.index[0], top_k=4)
    mags = [abs(a.shap_value) for a in attrs]
    assert mags == sorted(mags, reverse=True)


def test_jumlah_faktor_mengikuti_top_k(fitted):
    ex, X, _ = fitted
    assert len(ex.explain_child(X, X.index[3], top_k=3)) == 3


def test_baris_tidak_ada_ditolak(fitted):
    ex, X, _ = fitted
    with pytest.raises(KeyError):
        ex.explain_child(X, 999999)


def test_arah_konsisten_dengan_nilai_yang_ditampilkan(fitted):
    from tabular.explain import direction_for, displayed_shap
    ex, X, _ = fitted
    for a in ex.explain_child(X, X.index[5], top_k=4):
        assert a.direction == direction_for(displayed_shap(a.shap_value), atol=0.0)


def test_importance_global_menemukan_fitur_yang_ditanamkan(fitted):
    """Label dibangkitkan didominasi slope; SHAP harus menempatkannya teratas."""
    ex, X, _ = fitted
    imp = ex.global_importance(X)
    assert imp.iloc[0]["feature"] == "haz_slope_per_month"
    assert (imp["mean_abs_shap"] >= 0).all()


def test_importance_global_terurut(fitted):
    ex, X, _ = fitted
    v = ex.global_importance(X)["mean_abs_shap"].to_numpy()
    assert (np.diff(v) <= 1e-12).all()


def test_explain_batch_satu_baris_per_faktor(fitted):
    ex, X, _ = fitted
    sub = X.head(6)
    out = ex.explain_batch(sub, top_k=3)
    assert len(out) == 6 * 3
    assert set(out["rank"]) == {1, 2, 3}
    assert out.groupby("row_index").size().eq(3).all()


def test_kalimat_dashboard_netral_tanpa_klaim_sebab_akibat(fitted):
    ex, X, _ = fitted
    kalimat = to_sentences(ex.explain_child(X, X.index[1], top_k=3))
    assert len(kalimat) == 3
    gabung = " ".join(kalimat).lower()
    for terlarang in ("menyebabkan", "penyebab", "karena", "akibat"):
        assert terlarang not in gabung, "penjelasan tidak boleh berbunyi kausal"


def test_disclaimer_menolak_tafsir_kausal_dan_diagnosis():
    d = DISCLAIMER.lower()
    assert "bukan penyebab" in d
    assert "tenaga kesehatan" in d


def test_as_dict_aman_untuk_json(fitted):
    ex, X, _ = fitted
    d = ex.explain_child(X, X.index[0], top_k=1)[0].as_dict()
    assert set(d) == {"feature", "label", "value", "shap_value", "direction"}
    assert isinstance(d["shap_value"], float)


def test_nilai_kosong_menjadi_none_bukan_nan(fitted):
    from tabular.explain import Attribution
    a = Attribution("haz_t", "Status", float("nan"), 0.5, "menaikkan")
    assert a.as_dict()["value"] is None


def test_shap_nol_disebut_netral_bukan_menurunkan():
    from tabular.explain import Attribution, direction_for
    assert direction_for(0.0) == "netral"
    assert direction_for(-0.0) == "netral"
    assert direction_for(1e-15) == "netral"
    a = Attribution("haz_t", "Status panjang badan saat ini", -1.0, 0.0, direction_for(0.0))
    kalimat = to_sentences([a])[0]
    assert "menurunkan" not in kalimat
    assert "tidak mengubah" in kalimat


def test_arah_untuk_nilai_jelas_tetap_benar():
    from tabular.explain import direction_for
    assert direction_for(0.4) == "menaikkan"
    assert direction_for(-0.4) == "menurunkan"


def test_explain_batch_tidak_pernah_memberi_arah_pada_nol(fitted):
    ex, X, _ = fitted
    out = ex.explain_batch(X.head(20), top_k=4)
    nol = out[out["shap_value"] == 0.0]
    assert (nol["direction"] == "netral").all()


def test_shap_yang_membulat_ke_nol_disebut_netral():
    """0.00004 tampil sebagai 0.0 di CSV; arahnya tidak boleh 'menaikkan'."""
    from tabular.explain import direction_for, displayed_shap
    shown = displayed_shap(0.00004)
    assert shown == 0.0
    assert direction_for(shown, atol=0.0) == "netral"


def test_csv_tidak_pernah_memuat_nol_dengan_arah(fitted):
    ex, X, _ = fitted
    out = ex.explain_batch(X.head(30), top_k=4)
    nol = out[out["shap_value"] == 0.0]
    assert (nol["direction"] == "netral").all()


def test_nilai_kecil_di_atas_ambang_tampil_tetap_berarah():
    from tabular.explain import direction_for, displayed_shap
    shown = displayed_shap(0.00006)
    assert shown == 0.0001
    assert direction_for(shown, atol=0.0) == "menaikkan"
