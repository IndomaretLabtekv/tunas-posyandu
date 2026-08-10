"""Verifikasi metrik ranking dan klasifikasi (TAB-06, TAB-07)."""

import numpy as np
import pandas as pd
import pytest

from tabular.evaluate import (
    compare_models,
    error_analysis,
    evaluate_all,
    evaluate_calibration,
    evaluate_ranking,
    lift_at_k,
    precision_at_k,
    recall_at_k,
    slice_report,
)


def test_ranking_sempurna_menangkap_semua_positif():
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    s = [0.9, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]
    assert recall_at_k(y, s, 0.20) == 1.0
    assert precision_at_k(y, s, 0.20) == 1.0


def test_ranking_terbalik_tidak_menangkap_apa_pun():
    y = [1, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    s = [0.1, 0.1, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9]
    assert recall_at_k(y, s, 0.20) == 0.0


def test_recall_at_k_naik_seiring_k(rng=np.random.default_rng(0)):
    y = rng.integers(0, 2, 500)
    s = rng.random(500)
    vals = [recall_at_k(y, s, k) for k in (0.05, 0.10, 0.20, 0.50, 1.0)]
    assert all(a <= b + 1e-9 for a, b in zip(vals, vals[1:]))
    assert vals[-1] == pytest.approx(1.0)


def test_lift_satu_untuk_skor_acak():
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 5000)
    s = rng.random(5000)
    assert lift_at_k(y, s, 0.20) == pytest.approx(1.0, abs=0.15)


def test_k_frac_tidak_valid_ditolak():
    for k in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            recall_at_k([1, 0], [0.5, 0.5], k)


def test_nan_diabaikan_bukan_menggagalkan():
    y = [1, np.nan, 0, 1]
    s = [0.9, 0.8, np.nan, 0.7]
    out = evaluate_ranking(y, s)
    assert out["n"] == 2 and out["n_positive"] == 2


def test_semua_nan_ditolak():
    with pytest.raises(ValueError, match="valid"):
        evaluate_ranking([np.nan, np.nan], [np.nan, np.nan])


def test_panjang_berbeda_ditolak():
    with pytest.raises(ValueError, match="Panjang berbeda"):
        recall_at_k([1, 0, 1], [0.5, 0.5], 0.5)


def test_tanpa_positif_menghasilkan_nan_bukan_nol():
    assert np.isnan(recall_at_k([0, 0, 0, 0], [0.9, 0.8, 0.7, 0.6], 0.5))


def test_skor_bukan_probabilitas_tidak_diberi_brier():
    out = evaluate_calibration([1, 0, 1], [3.2, -1.0, 5.5])
    assert not out["is_probability"] and np.isnan(out["brier"])


def test_probabilitas_diberi_brier():
    out = evaluate_calibration([1, 0, 1], [0.9, 0.1, 0.8])
    assert out["is_probability"] and 0 <= out["brier"] <= 1


def test_accuracy_tidak_disediakan():
    """Pada kelas minoritas ~15%, accuracy menyesatkan dan sengaja tidak ada."""
    out = evaluate_all([1, 0, 0, 0], [0.9, 0.2, 0.1, 0.1], score_type="probability", operating_k=0.25)
    assert "accuracy" not in out


def test_ambang_kapasitas_menandai_tepat_k_persen():
    from tabular.evaluate import capacity_threshold
    rng = np.random.default_rng(9)
    s = rng.random(1000)
    thr = capacity_threshold(s, 0.20)
    assert 0.18 <= (s >= thr).mean() <= 0.22


def test_ambang_wajib_eksplisit_pada_evaluate_classification():
    """Tidak ada default 0.5 -- pada tugas ini nilai itu hampir selalu salah."""
    from tabular.evaluate import evaluate_classification
    with pytest.raises(TypeError):
        evaluate_classification([1, 0], [0.9, 0.1])


def test_skor_probabilitas_rendah_tidak_menghasilkan_f1_nol():
    """Regresi: prevalensi ~16% membuat semua probabilitas < 0.5, sehingga
    ambang 0.5 menghasilkan F1 = 0 padahal rankingnya baik."""
    rng = np.random.default_rng(10)
    n = 1000
    y = (rng.random(n) < 0.16).astype(int)
    s = np.clip(0.05 + 0.25 * y + rng.normal(0, 0.05, n), 0, 0.45)
    out = evaluate_all(y, s, score_type="probability", operating_k=0.20)
    assert s.max() < 0.5
    assert out["f1"] > 0.3


def test_titik_operasi_dilaporkan():
    out = evaluate_all([1, 0, 1, 0, 0], [0.4, 0.1, 0.3, 0.2, 0.05], score_type="probability", operating_k=0.20)
    assert out["operating_point"] == "top-20%"


def test_evaluate_all_memuat_metrik_kunci():
    y = [1, 0, 1, 0, 0, 1, 0, 0, 0, 0]
    s = [0.9, 0.2, 0.8, 0.3, 0.1, 0.7, 0.4, 0.2, 0.1, 0.05]
    out = evaluate_all(y, s, score_type="probability")
    for key in ("auprc", "recall@20%", "precision@20%", "f1", "tp", "fn",
                "raw_brier", "score_type"):
        assert key in out


def test_compare_models_menghasilkan_tabel():
    y = [1, 0, 1, 0, 0, 1, 0, 0]
    res = {
        "B0": evaluate_all(y, [0.9, 0.2, 0.8, 0.3, 0.1, 0.7, 0.4, 0.2], score_type="probability"),
        "M1": evaluate_all(y, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], score_type="probability"),
    }
    df = compare_models(res)
    assert set(df["model"]) == {"B0", "M1"} and "auprc" in df.columns


def test_slice_report_menandai_irisan_kecil():
    rng = np.random.default_rng(3)
    n = 200
    y = rng.integers(0, 2, n)
    s = rng.random(n)
    sl = pd.DataFrame({"sex": ["M"] * 190 + ["F"] * 10})
    rep = slice_report(y, s, sl, min_n=30)
    assert rep.loc[rep["value"] == "F", "underpowered"].iloc[0]
    assert not rep.loc[rep["value"] == "M", "underpowered"].iloc[0]


def test_error_analysis_memisahkan_empat_kelompok():
    y = [1, 1, 0, 0]
    s = [0.9, 0.1, 0.9, 0.1]
    feats = pd.DataFrame({"haz_t": [-2.5, -1.0, -3.0, 0.5]})
    rep = error_analysis(y, s, feats)
    assert set(rep["group"]) == {"true_positive", "false_negative", "false_positive", "true_negative"}
    assert rep["n"].sum() == 4
