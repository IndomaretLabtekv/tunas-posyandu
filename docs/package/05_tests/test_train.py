"""Regression test untuk experiment runner (TAB-04, TAB-05).

Setiap test di sini menutup satu kebocoran atau kesalahan metodologis yang
pernah nyata terjadi pada versi sebelumnya.
"""

import numpy as np
import pandas as pd
import pytest

from tabular.baselines import B0Model, fit_b1, rule_stunted_now
from tabular.evaluate import (
    capacity_predictions,
    capacity_threshold,
    evaluate_all,
    recall_at_k,
)
from tabular.splits import temporal_split


# ---------------------------------------------------------------- exact top-K

def test_top_k_dengan_skor_kembar_memilih_tepat_k():
    """Ambang kuantil melebihi K saat ada tie; pemilihan indeks tidak."""
    s = np.array([0.9, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    pred = capacity_predictions(s, 0.20)
    assert pred.sum() == 2
    # bukti bahwa pendekatan lama gagal:
    assert (s >= capacity_threshold(s, 0.20)).sum() == 3


def test_top_k_pada_skor_konstan_tetap_k():
    s = np.full(10, 0.5)
    assert capacity_predictions(s, 0.20).sum() == 2
    assert (s >= capacity_threshold(s, 0.20)).sum() == 10


def test_top_k_dan_recall_at_k_memakai_daftar_yang_sama():
    rng = np.random.default_rng(0)
    y = (rng.random(200) < 0.2).astype(int)
    s = np.round(rng.random(200), 2)          # banyak tie
    pred = capacity_predictions(s, 0.20)
    manual = (y * pred).sum() / y.sum()
    assert manual == pytest.approx(recall_at_k(y, s, 0.20))


def test_tie_break_membuat_urutan_reprodusibel():
    s = np.array([0.5, 0.5, 0.5, 0.5])
    ids = np.array(["C003", "C001", "C004", "C002"])
    a = capacity_predictions(s, 0.5, ids)
    b = capacity_predictions(s[::-1], 0.5, ids[::-1])[::-1]
    assert (a == b).all()


def test_skor_tidak_finite_ditolak():
    with pytest.raises(ValueError, match="NaN atau inf"):
        capacity_predictions(np.array([0.5, np.nan]), 0.5)


# ---------------------------------------------------------------- RULE

def test_aturan_biner_tidak_mendapat_metrik_ranking():
    rng = np.random.default_rng(1)
    y = (rng.random(200) < 0.2).astype(int)
    s = rule_stunted_now(pd.DataFrame({"haz_t": rng.normal(-1, 1, 200)}))
    out = evaluate_all(y, s, score_type="binary_rule")
    for key in ("auprc", "recall@20%", "precision@20%", "raw_brier"):
        assert np.isnan(out[key]), f"{key} tidak boleh diisi untuk aturan biner"
    assert out["f1"] >= 0 and out["operating_point"].startswith("rule")


def test_score_type_wajib_dikenal():
    with pytest.raises(ValueError, match="score_type"):
        evaluate_all([1, 0], [0.9, 0.1], score_type="magic")


def test_skor_ranking_tidak_mendapat_brier():
    out = evaluate_all([1, 0, 1, 0], [3.2, -1.0, 5.5, 0.2], score_type="ranking")
    assert np.isnan(out["raw_brier"]) and not np.isnan(out["auprc"])


# ---------------------------------------------------------------- B1 & B0

@pytest.fixture
def frame():
    rng = np.random.default_rng(2)
    n = 300
    return pd.DataFrame({
        "haz_t": rng.normal(-1.0, 1.2, n),
        "haz_slope_per_month": rng.normal(-0.02, 0.05, n),
    })


def test_skor_b1_tidak_berubah_karena_anggota_batch_lain(frame):
    """Peringkat dua anak tidak boleh bergantung pada siapa lagi yang ikut dibatch."""
    rng = np.random.default_rng(3)
    y = (rng.random(len(frame)) < 0.2).astype(float)
    model = fit_b1(frame, frame, y)

    a = frame.iloc[[0, 1]]
    batch1 = pd.concat([a, frame.iloc[2:10]])
    batch2 = pd.concat([a, frame.iloc[100:180]])   # anggota lain sangat berbeda

    s1 = model.predict(batch1)[:2]
    s2 = model.predict(batch2)[:2]
    assert np.allclose(s1, s2), "skor B1 bergantung pada batch -> test-distribution leakage"


def test_b1_preprocessing_dipelajari_dari_train_saja(frame):
    y = np.zeros(len(frame))
    m = fit_b1(frame, frame, y)
    for attr in ("haz_fill", "haz_mean", "haz_std", "slope_fill", "slope_mean", "slope_std"):
        assert np.isfinite(getattr(m, attr))


def test_b0_memberi_prioritas_terendah_pada_haz_kosong():
    X = pd.DataFrame({"haz_t": [-3.0, np.nan, 0.5]})
    s = B0Model().predict(X)
    assert np.isfinite(s).all()
    assert s[1] == s.min(), "haz_t kosong harus berprioritas terendah, bukan diisi median"


def test_b0_tidak_memakai_statistik_batch():
    """Skor anak yang sama tidak berubah karena anggota batch lain."""
    a = pd.DataFrame({"haz_t": [-2.0]})
    b1 = B0Model().predict(pd.concat([a, pd.DataFrame({"haz_t": [0.0, 1.0]})]))[0]
    b2 = B0Model().predict(pd.concat([a, pd.DataFrame({"haz_t": [-5.0, -6.0]})]))[0]
    assert b1 == b2


# ---------------------------------------------------------------- temporal

def _temporal_frame():
    return pd.DataFrame({
        "child_id": [f"C{i:02d}" for i in range(12)],
        "prediction_date": pd.to_datetime(
            ["2025-01-01"] * 4 + ["2025-02-01"] * 4 + ["2025-06-01"] * 4
        ),
        # dua baris pra-cutoff labelnya baru matang SETELAH cutoff
        "label_available_date": pd.to_datetime(
            ["2025-04-01", "2025-04-05", "2025-07-01", "2025-07-15"]
            + ["2025-05-01"] * 4
            + ["2025-09-01"] * 4
        ),
    })


def test_label_belum_matang_dipurge_dari_train():
    df = _temporal_frame()
    split = temporal_split(df, date_col="prediction_date", test_start="2025-06-01",
                           val_frac=0.0, label_available_col="label_available_date")
    pool = set(split.train) | set(split.val)
    avail = df["label_available_date"]
    assert all(avail.loc[i] < pd.Timestamp("2025-06-01") for i in pool)
    assert "purged_unmatured=2" in split.kind


def test_tanpa_purge_label_masa_depan_ikut_masuk_train():
    """Kontrol: tanpa kolom maturasi, kebocoran memang terjadi."""
    df = _temporal_frame()
    split = temporal_split(df, date_col="prediction_date", test_start="2025-06-01", val_frac=0.0)
    pool = set(split.train) | set(split.val)
    avail = df["label_available_date"]
    assert any(avail.loc[i] >= pd.Timestamp("2025-06-01") for i in pool)


def test_kolom_maturasi_tidak_ada_ditolak():
    df = _temporal_frame().drop(columns=["label_available_date"])
    with pytest.raises(ValueError, match="label_available_date"):
        temporal_split(df, date_col="prediction_date", test_start="2025-06-01",
                       label_available_col="label_available_date")


# ---------------------------------------------------------------- primary model

def test_primary_model_ditetapkan_di_muka_bukan_m3():
    from tabular.train import ExperimentConfig
    cfg = ExperimentConfig()
    assert cfg.primary_model == "M2_plus_trajectory"
    assert "pre-specified" in cfg.selection_rule


def test_primary_model_tidak_dikenal_ditolak(tmp_path):
    from tabular.train import ExperimentConfig, run
    cfg = ExperimentConfig(primary_model="M9_imaginary", data_path=tmp_path / "none.csv")
    with pytest.raises((ValueError, FileNotFoundError)):
        run(cfg)


# ---------------------------------------------------------------- konsistensi tie-break

def test_ranking_dan_klasifikasi_memakai_tie_break_yang_sama():
    """Tanpa ini, Recall@K bisa 1.0 sementara confusion matrix 0.0 pada data sama."""
    y = np.array([1, 0, 0, 0, 0])
    s = np.array([0.9, 0.9, 0.9, 0.1, 0.1])
    ids = np.array(["C3", "C1", "C2", "C4", "C5"])
    out = evaluate_all(y, s, score_type="ranking", operating_k=0.40,
                       k_fractions=(0.40,), tie_break=ids)
    assert out["recall@40%"] == out["recall"]
    assert out["precision@40%"] == out["precision"]


def test_tanpa_tie_break_pun_tetap_konsisten():
    rng = np.random.default_rng(7)
    y = (rng.random(300) < 0.2).astype(int)
    s = np.round(rng.random(300), 2)
    out = evaluate_all(y, s, score_type="ranking", operating_k=0.20, k_fractions=(0.20,))
    assert out["recall@20%"] == out["recall"]


def test_score_type_wajib_diberikan():
    with pytest.raises(TypeError):
        evaluate_all([1, 0], [0.8, 0.2])


# ---------------------------------------------------------------- unit evaluasi

def _visits():
    return pd.DataFrame({
        "child_id": ["A", "A", "A", "B", "B", "C"],
        "prediction_date": pd.to_datetime(
            ["2025-01-01", "2025-02-01", "2025-03-01",
             "2025-01-15", "2025-02-15", "2025-01-20"]
        ),
    })


def test_unit_evaluasi_satu_baris_per_anak():
    from tabular.train import select_index_visits
    df = _visits()
    for kind in ("grouped", "temporal"):
        idx = select_index_visits(df, kind)
        assert df.loc[idx, "child_id"].is_unique
        assert len(idx) == df["child_id"].nunique()


def test_grouped_memilih_kunjungan_terakhir():
    from tabular.train import select_index_visits
    df = _visits()
    picked = df.loc[select_index_visits(df, "grouped")]
    assert picked.loc[picked.child_id == "A", "prediction_date"].iloc[0] == pd.Timestamp("2025-03-01")


def test_temporal_memilih_kunjungan_pertama():
    from tabular.train import select_index_visits
    df = _visits()
    picked = df.loc[select_index_visits(df, "temporal")]
    assert picked.loc[picked.child_id == "A", "prediction_date"].iloc[0] == pd.Timestamp("2025-01-01")


def test_aturan_index_visit_tidak_bergantung_skor_model():
    """Aturan ditetapkan di muka; mengurutkan ulang baris tidak mengubah pilihan."""
    from tabular.train import select_index_visits
    df = _visits()
    a = set(select_index_visits(df, "grouped"))
    b = set(select_index_visits(df.iloc[::-1], "grouped"))
    assert a == b


def test_validation_dan_test_memakai_unit_yang_sama(tmp_path):
    """Objektif tuning harus sama dengan objektif penilaian akhir.

    Kalau validation memakai seluruh kunjungan, anak yang lebih sering datang
    berbobot 10-20 kali saat memilih bobot B1 dan best_iteration -- padahal di
    test berbobot satu. Dengan attendance MNAR, itu menggeser perbandingan.
    """
    import warnings
    import pandas as pd

    from data.generate_synth import SynthConfig, generate
    from tabular.train import ExperimentConfig, run
    from tabular.who_lms import MAX_AGE_DAYS, haz_series

    rows = []
    for sex, m0 in (("M", 49.9), ("F", 49.1)):
        for a in range(0, MAX_AGE_DAYS + 31, 10):
            rows.append({"sex": sex, "age_days": a, "L": 1.0,
                         "M": m0 + 0.0305 * a, "S": 0.038 + 0.000002 * a})
    tbl = pd.DataFrame(rows)

    df = generate(SynthConfig(n_children=200, seed=1), table=tbl)
    df["haz"] = haz_series(df, tbl)
    data = tmp_path / "cohort.csv"
    df.to_csv(data, index=False)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = run(ExperimentConfig(data_path=data, out_dir=tmp_path / "out"))

    sizes = res["manifest"]["split_sizes"]
    assert sizes["val_index_visits"] < sizes["val_all_visits"]
    assert sizes["test_index_visits"] < sizes["test_all_visits"]
    assert res["manifest"]["validation_unit"] == "one_latest_eligible_visit_per_child"


def test_b0_missing_score_konstan_lintas_batch():
    """Skor baris kosong tidak boleh bergantung pada isi batch."""
    from tabular.baselines import B0Model
    m = B0Model()
    a = m.predict(pd.DataFrame({"haz_t": [np.nan, -1.0]}))[0]
    b = m.predict(pd.DataFrame({"haz_t": [np.nan, -9.0, 3.0]}))[0]
    assert a == b == m.missing_score


# ---------------------------------------------------------------- slice report

def _slice_fixture():
    y = np.array([1, 0, 1, 0, 1, 0])
    s = np.array([0.9, 0.9, 0.9, 0.1, 0.1, 0.1])
    ids = np.array(["C1", "C2", "C3", "C4", "C5", "C6"])
    sl = pd.DataFrame({"sex": ["M", "M", "M", "F", "F", "F"]})
    return y, s, ids, sl


def test_slice_report_memakai_daftar_prioritas_global():
    """Top-K per irisan menyembunyikan disparitas; top-K global menampakkannya."""
    from tabular.evaluate import capacity_predictions, slice_report
    y, s, ids, sl = _slice_fixture()
    selected = capacity_predictions(s, 0.5, ids)          # 3 teratas semuanya M
    rep = slice_report(y, s, sl, selected=selected, min_n=1)

    f = rep[rep["value"] == "F"].iloc[0]
    m = rep[rep["value"] == "M"].iloc[0]
    assert f["selection_rate"] == 0.0, "kelompok F tidak masuk daftar prioritas global"
    assert m["selection_rate"] == 1.0
    assert f["recall_at_global_capacity"] == 0.0


def test_slice_report_stabil_terhadap_urutan_baris():
    from tabular.evaluate import capacity_predictions, slice_report
    y, s, ids, sl = _slice_fixture()
    sel = capacity_predictions(s, 0.5, ids)
    a = slice_report(y, s, sl, selected=sel, min_n=1).set_index("value")

    order = np.array([4, 0, 5, 2, 1, 3])
    b = slice_report(y[order], s[order], sl.iloc[order],
                     selected=sel[order], min_n=1).set_index("value")
    for v in ("M", "F"):
        assert a.loc[v, "selection_rate"] == b.loc[v, "selection_rate"]
        assert a.loc[v, "recall_at_global_capacity"] == b.loc[v, "recall_at_global_capacity"]


def test_slice_report_tanpa_selected_tetap_memberi_auprc():
    from tabular.evaluate import slice_report
    y, s, _, sl = _slice_fixture()
    rep = slice_report(y, s, sl, min_n=1)
    assert "auprc" in rep.columns
    assert "selection_rate" not in rep.columns


def test_b1_menolak_training_tanpa_nilai_valid():
    from tabular.baselines import fit_b1
    X = pd.DataFrame({"haz_t": [np.nan, np.nan], "haz_slope_per_month": [np.nan, np.nan]})
    with pytest.raises(ValueError, match="minimal satu nilai valid"):
        fit_b1(X, X, np.array([0.0, 1.0]))
