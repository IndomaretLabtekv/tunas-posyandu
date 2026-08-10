"""Verifikasi definisi target DEC-010, termasuk seluruh aturan kasus tepi."""

import pandas as pd
import pytest

from tabular.target import (
    HAZ_DROP_THRESHOLD,
    attach_labels,
    drop_report,
    label_visits,
)


def make(rows):
    return pd.DataFrame(rows, columns=["child_id", "visit_date", "age_days", "haz"])


def test_penurunan_haz_melewati_ambang_diberi_label_1():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -1.6),  # turun 0.6 SD pada 91 hari
    ])
    assert label_visits(df).label.iloc[0] == 1.0


def test_penurunan_tepat_di_ambang_dihitung_deteriorasi():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -1.0 - HAZ_DROP_THRESHOLD),
    ])
    assert label_visits(df).label.iloc[0] == 1.0


def test_penurunan_di_bawah_ambang_diberi_label_0():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -1.3),
    ])
    assert label_visits(df).label.iloc[0] == 0.0


def test_melintasi_ambang_minus_dua_dihitung_meski_turun_sedikit():
    df = make([
        ("A", "2025-01-01", 200, -1.9),
        ("A", "2025-04-02", 291, -2.1),  # turun 0.2 SD saja, tapi melintas
    ])
    assert label_visits(df).label.iloc[0] == 1.0


def test_membaik_diberi_label_0():
    df = make([
        ("A", "2025-01-01", 200, -2.5),
        ("A", "2025-04-02", 291, -1.8),
    ])
    assert label_visits(df).label.iloc[0] == 0.0


def test_severely_stunted_tetap_disertakan():
    df = make([
        ("A", "2025-01-01", 200, -3.4),
        ("A", "2025-04-02", 291, -4.0),
    ])
    res = label_visits(df)
    assert res.label.iloc[0] == 1.0
    assert pd.isna(res.drop_reason.iloc[0])


def test_tanpa_followup_dalam_jendela_dibuang():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-08-01", 412, -2.0),  # 212 hari, di luar jendela
    ])
    res = label_visits(df)
    assert pd.isna(res.label.iloc[0])
    assert res.drop_reason.iloc[0] == "no_followup_in_window"


def test_followup_terlalu_dini_juga_di_luar_jendela():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-02-01", 231, -2.0),  # 31 hari < 49
    ])
    assert label_visits(df).drop_reason.iloc[0] == "no_followup_in_window"


def test_beberapa_followup_dipakai_yang_terdekat_ke_horizon():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-02-25", 255, -3.0),  # 55 hari: dalam jendela, jauh dari 91
        ("A", "2025-04-02", 291, -1.1),  # 91 hari: tepat horizon
    ])
    assert label_visits(df).label.iloc[0] == 0.0


def test_followup_melewati_batas_usia_mvp_dibuang():
    df = make([
        ("A", "2025-01-01", 700, -1.0),
        ("A", "2025-04-02", 791, -2.0),  # > 730 hari
    ])
    assert label_visits(df).drop_reason.iloc[0] == "followup_age_out_of_mvp_range"


def test_baseline_haz_kosong_diberi_alasan_baseline():
    df = make([
        ("A", "2025-01-01", 200, float("nan")),
        ("A", "2025-04-02", 291, -2.0),
    ])
    assert label_visits(df).drop_reason.iloc[0] == "baseline_missing_haz"


def test_followup_haz_kosong_diberi_alasan_followup():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, float("nan")),
    ])
    assert label_visits(df).drop_reason.iloc[0] == "followup_missing_haz"


def test_baseline_usia_kosong_ditolak():
    df = make([
        ("A", "2025-01-01", float("nan"), -1.0),
        ("A", "2025-04-02", 291, -3.0),
    ])
    res = label_visits(df)
    assert pd.isna(res.label.iloc[0]), "usia baseline NaN tidak boleh menghasilkan label"
    assert res.drop_reason.iloc[0] == "baseline_age_out_of_mvp_range"


def test_baseline_usia_di_luar_rentang_ditolak():
    df = make([
        ("A", "2025-01-01", 800, -1.0),
        ("A", "2025-04-02", 891, -3.0),
    ])
    assert label_visits(df).drop_reason.iloc[0] == "baseline_age_out_of_mvp_range"


def test_visit_date_tidak_valid_ditolak():
    df = make([
        ("A", "bukan-tanggal", 200, -1.0),
        ("A", "2025-04-02", 291, -2.0),
    ])
    with pytest.raises(ValueError, match="visit_date"):
        label_visits(df)


def test_semua_alasan_drop_terdaftar():
    from tabular.target import DROP_REASONS
    df = make([
        ("A", "2025-01-01", 200, float("nan")),
        ("A", "2025-04-02", 291, -2.0),
        ("B", "2025-01-01", 800, -1.0),
        ("B", "2025-04-02", 891, -3.0),
        ("C", "2025-01-01", 200, -1.0),
    ])
    reasons = set(label_visits(df).drop_reason.dropna())
    assert reasons.issubset(DROP_REASONS), f"alasan tak terdaftar: {reasons - DROP_REASONS}"


def test_tidak_ada_kebocoran_antar_anak():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("B", "2025-04-02", 291, -3.0),  # anak lain, bukan follow-up A
    ])
    res = label_visits(df)
    assert res.drop_reason.iloc[0] == "no_followup_in_window"
    assert res.drop_reason.iloc[1] == "no_followup_in_window"


def test_kolom_wajib_divalidasi():
    with pytest.raises(ValueError, match="Kolom hilang"):
        label_visits(pd.DataFrame({"child_id": ["A"]}))


def test_drop_report_menjumlah_seratus_persen():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -1.8),
        ("B", "2025-01-01", 300, -2.5),
    ])
    rep = drop_report(attach_labels(df))
    assert abs(rep["pct"].sum() - 100.0) < 1e-6
    assert rep["n"].sum() == len(df)


def test_followup_usia_negatif_ditolak():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", -1, -3.0),
    ])
    res = label_visits(df)
    assert pd.isna(res.label.iloc[0])
    assert res.drop_reason.iloc[0] == "followup_age_out_of_mvp_range"


def test_index_tidak_unik_ditolak():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -2.0),
    ])
    df.index = [0, 0]
    with pytest.raises(ValueError, match="unik"):
        label_visits(df)


def test_child_id_string_kosong_ditolak():
    df = make([
        ("   ", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 291, -2.0),
    ])
    with pytest.raises(ValueError, match="child_id"):
        label_visits(df)


def test_followup_usia_harus_bertambah():
    df = make([
        ("A", "2025-01-01", 200, -1.0),
        ("A", "2025-04-02", 100, -2.0),  # usia mundur -> korupsi data
    ])
    res = label_visits(df)
    assert pd.isna(res.label.iloc[0])
    assert res.drop_reason.iloc[0] == "followup_age_not_after_baseline"


def test_toleransi_tidak_boleh_mencakup_baseline():
    df = make([("A", "2025-01-01", 200, -1.0)])
    with pytest.raises(ValueError, match="tolerance_days"):
        label_visits(df, horizon_days=30, tolerance_days=40)


def test_horizon_tidak_boleh_nol_atau_negatif():
    df = make([("A", "2025-01-01", 200, -1.0)])
    with pytest.raises(ValueError, match="horizon_days"):
        label_visits(df, horizon_days=0)


def test_baris_tunggal_tidak_menjadi_followup_dirinya_sendiri():
    df = make([("A", "2025-01-01", 200, -1.0)])
    res = label_visits(df)
    assert pd.isna(res.label.iloc[0])
    assert res.drop_reason.iloc[0] == "no_followup_in_window"
