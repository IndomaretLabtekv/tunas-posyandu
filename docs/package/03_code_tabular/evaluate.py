"""Metrik evaluasi: klasifikasi, ranking, dan kalibrasi (TAB-06, TAB-07).

Produk Tunas menghasilkan **urutan prioritas**, bukan sekadar klasifikasi. Karena
kapasitas tindak lanjut petugas gizi terbatas, metrik yang paling dekat dengan
kondisi nyata adalah Recall@K: berapa kasus deteriorasi tertangkap bila hanya
K% teratas yang ditindaklanjuti. Inilah angka yang menjadi narasi
*before -> after* di paper.

Accuracy sengaja TIDAK disediakan. Pada kelas minoritas ~15%, menebak "tidak
deteriorasi" untuk semua anak sudah menghasilkan accuracy ~85% tanpa nilai guna
apa pun. AUPRC dan metrik @K jauh lebih informatif pada kondisi tidak seimbang.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

DEFAULT_K_FRACTIONS = (0.05, 0.10, 0.20)


def _clean_with_tie(y_true, y_score, tie_break=None):
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(y_score, dtype=float)
    if y.shape != s.shape:
        raise ValueError(f"Panjang berbeda: y_true {y.shape} vs y_score {s.shape}")
    mask = np.isfinite(y) & np.isfinite(s)
    if not mask.any():
        raise ValueError("Tidak ada pasangan (label, skor) yang valid.")
    tb = None if tie_break is None else np.asarray(tie_break)[mask]
    return y[mask], s[mask], tb


def _clean(y_true, y_score) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(y_score, dtype=float)
    if y.shape != s.shape:
        raise ValueError(f"Panjang berbeda: y_true {y.shape} vs y_score {s.shape}")
    mask = np.isfinite(y) & np.isfinite(s)
    if not mask.any():
        raise ValueError("Tidak ada pasangan (label, skor) yang valid.")
    return y[mask], s[mask]


def recall_at_k(y_true, y_score, k_frac: float, tie_break=None) -> float:
    """Proporsi kasus positif yang tertangkap dalam K% teratas.

    Memakai `capacity_predictions()` yang sama dengan metrik klasifikasi @K,
    termasuk `tie_break`-nya. Kalau tidak, dua metrik bisa memakai dua daftar
    prioritas berbeda saat ada skor kembar -- Recall@K melaporkan 1.0 sementara
    confusion matrix melaporkan 0.0 pada data yang sama.
    """
    y, s, tb = _clean_with_tie(y_true, y_score, tie_break)
    if y.sum() == 0:
        return float("nan")
    pred = capacity_predictions(s, k_frac, tb)
    return float((y * pred).sum() / y.sum())


def precision_at_k(y_true, y_score, k_frac: float, tie_break=None) -> float:
    """Proporsi kasus positif di antara K% teratas."""
    y, s, tb = _clean_with_tie(y_true, y_score, tie_break)
    pred = capacity_predictions(s, k_frac, tb)
    return float(y[pred == 1].mean())


def lift_at_k(y_true, y_score, k_frac: float, tie_break=None) -> float:
    """Precision@K dibagi prevalensi -- berapa kali lebih baik daripada acak."""
    y, _, _ = _clean_with_tie(y_true, y_score, tie_break)
    base = y.mean()
    if base == 0:
        return float("nan")
    return precision_at_k(y_true, y_score, k_frac, tie_break) / base


def evaluate_ranking(y_true, y_score, k_fractions=DEFAULT_K_FRACTIONS, tie_break=None) -> dict:
    """Metrik yang tidak membutuhkan ambang keputusan."""
    y, s = _clean(y_true, y_score)
    out = {
        "n": int(len(y)),
        "n_positive": int(y.sum()),
        "prevalence": round(float(y.mean()), 4),
        "auprc": round(float(average_precision_score(y, s)), 4),
        "roc_auc": round(float(roc_auc_score(y, s)), 4) if 0 < y.sum() < len(y) else float("nan"),
    }
    for k in k_fractions:
        pct = int(round(k * 100))
        out[f"recall@{pct}%"] = round(recall_at_k(y_true, y_score, k, tie_break), 4)
        out[f"precision@{pct}%"] = round(precision_at_k(y_true, y_score, k, tie_break), 4)
        out[f"lift@{pct}%"] = round(lift_at_k(y_true, y_score, k, tie_break), 3)
    return out


def capacity_threshold(y_score, k_frac: float) -> float:
    """Nilai skor pada kuantil (1-k). INFORMASI saja.

    Jangan dipakai untuk menentukan anggota top-K: bila ada skor kembar (tie),
    `skor >= ambang` dapat menandai lebih dari K% baris. Pada skor biner seperti
    aturan `HAZ < -2`, "top-20%" bahkan bisa menandai 100% baris. Pakai
    `capacity_predictions()` yang memilih indeks secara eksak.
    """
    s = np.asarray(y_score, dtype=float)
    s = s[np.isfinite(s)]
    if not 0 < k_frac <= 1:
        raise ValueError("k_frac harus di (0, 1].")
    return float(np.quantile(s, 1 - k_frac))


def capacity_predictions(y_score, k_frac: float, tie_break=None) -> np.ndarray:
    """Tandai tepat K% baris berperingkat tertinggi sebagai prioritas.

    Pemilihan dilakukan lewat indeks terurut, bukan ambang kuantil, sehingga
    jumlah yang ditandai selalu tepat K% berapa pun banyaknya skor kembar.
    Ini juga membuat metrik @K dan F1 memakai daftar prioritas yang SAMA --
    sebelumnya keduanya bisa berasal dari dua daftar berbeda.

    `tie_break` (mis. `child_id`) membuat urutan reprodusibel dan tidak
    bergantung pada urutan baris dalam DataFrame.
    """
    s = np.asarray(y_score, dtype=float)
    if not 0 < k_frac <= 1:
        raise ValueError("k_frac harus di (0, 1].")
    if not np.isfinite(s).all():
        raise ValueError("Skor kapasitas tidak boleh NaN atau inf.")

    if tie_break is not None:
        tb = np.asarray(tie_break).astype(str)
        order = np.lexsort((tb, -s))
    else:
        order = np.argsort(-s, kind="stable")

    k = max(1, int(round(k_frac * len(s))))
    pred = np.zeros(len(s), dtype=int)
    pred[order[:k]] = 1
    return pred


def _metrics_from_pred(y: np.ndarray, pred: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
    }


def evaluate_classification(y_true, y_score, threshold: float) -> dict:
    """Metrik pada satu ambang keputusan.

    `threshold` wajib eksplisit -- tidak ada default 0.5, karena pada tugas ini
    (prevalensi ~16%) nilai itu hampir selalu menghasilkan nol prediksi positif.
    """
    y, s = _clean(y_true, y_score)
    out = _metrics_from_pred(y, (s >= threshold).astype(int))
    out["threshold"] = round(float(threshold), 6)
    return out


def evaluate_at_capacity(y_true, y_score, k_frac: float, tie_break=None) -> dict:
    """Metrik klasifikasi pada titik operasi kapasitas tindak lanjut."""
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(y_score, dtype=float)
    mask = np.isfinite(y) & np.isfinite(s)
    tb = None if tie_break is None else np.asarray(tie_break)[mask]
    pred = capacity_predictions(s[mask], k_frac, tb)
    out = _metrics_from_pred(y[mask], pred)
    out["operating_point"] = f"top-{int(round(k_frac * 100))}%"
    out["n_flagged"] = int(pred.sum())
    return out


def evaluate_calibration(y_true, y_score) -> dict:
    """Brier score MENTAH, tanpa kalibrasi probabilitas.

    Angka ini tidak membuktikan model terkalibrasi: pelatihan memakai
    pembobotan kelas (`scale_pos_weight` / `class_weight="balanced"`) yang
    menggeser keluaran `predict_proba`. Klaim kalibrasi memerlukan Platt atau
    isotonic scaling pada validation lalu pengukuran ulang pada test -- belum
    dilakukan pada versi semifinal.
    """
    y, s = _clean(y_true, y_score)
    if s.min() < 0 or s.max() > 1:
        return {"brier": float("nan"), "is_probability": False}
    return {"brier": round(float(brier_score_loss(y, s)), 4), "is_probability": True}


def evaluate_all(
    y_true, y_score, *,
    score_type: str,
    operating_k: float = 0.20,
    rule_threshold: float = 0.5,
    tie_break=None,
    k_fractions=DEFAULT_K_FRACTIONS,
) -> dict:
    """Metrik lengkap, disesuaikan dengan JENIS skor.

    `score_type` wajib dinyatakan, tidak ditebak dari rentang nilai:

        "probability"  keluaran probabilistik -> metrik ranking + kapasitas + raw_brier
        "ranking"      skor urutan non-probabilistik (B0/B1) -> tanpa Brier
        "binary_rule"  aturan 0/1 (HAZ < -2) -> HANYA metrik klasifikasi.
                       Skor biner tidak dapat mengurutkan anak dalam kelompok
                       yang sama, sehingga AUPRC dan metrik @K tidak bermakna
                       dan sengaja dikosongkan, bukan diisi angka arbitrer.
    """
    if score_type not in {"probability", "ranking", "binary_rule"}:
        raise ValueError(f"score_type tidak dikenal: {score_type!r}")

    if score_type == "binary_rule":
        out = {k: float("nan") for k in ("auprc", "roc_auc", "raw_brier")}
        for k in k_fractions:
            pct = int(round(k * 100))
            out[f"recall@{pct}%"] = float("nan")
            out[f"precision@{pct}%"] = float("nan")
            out[f"lift@{pct}%"] = float("nan")
        y, s = _clean(y_true, y_score)
        out.update({"n": int(len(y)), "n_positive": int(y.sum()),
                    "prevalence": round(float(y.mean()), 4)})
        out.update(evaluate_classification(y_true, y_score, rule_threshold))
        out["operating_point"] = f"rule(>={rule_threshold})"
        out["score_type"] = score_type
        return out

    out = dict(evaluate_ranking(y_true, y_score, k_fractions, tie_break))
    out.update(evaluate_at_capacity(y_true, y_score, operating_k, tie_break))
    if score_type == "probability":
        cal = evaluate_calibration(y_true, y_score)
        # `raw_brier`: dihitung TANPA kalibrasi probabilitas. Model dilatih dengan
        # pembobotan kelas, sehingga keluarannya belum tentu terkalibrasi --
        # angka ini tidak boleh dipakai untuk mengklaim model "well-calibrated".
        out["raw_brier"] = cal["brier"]
    else:
        out["raw_brier"] = float("nan")
    out["score_type"] = score_type
    return out


def compare_models(results: dict[str, dict]) -> pd.DataFrame:
    """Susun tabel perbandingan lintas model -- ini tabel utama paper 4.2."""
    df = pd.DataFrame(results).T
    df.index.name = "model"
    return df.reset_index()


def slice_report(
    y_true, y_score, slices: pd.DataFrame, *, selected=None, min_n: int = 30
) -> pd.DataFrame:
    """Metrik per irisan populasi (TAB-11).

    `selected` adalah daftar prioritas GLOBAL (keluaran `capacity_predictions`
    atas seluruh test set). Wajib diberikan bila ingin metrik kapasitas.

    Menghitung top-K secara terpisah di dalam tiap irisan adalah kesalahan yang
    menyembunyikan disparitas: seandainya anak perempuan tidak ada satu pun di
    top-20% global, top-K per irisan tetap akan memilih 20% anak perempuan
    terbaik dan melaporkan recall yang tampak sehat. Yang ingin diketahui justru
    sebaliknya -- berapa banyak dari tiap kelompok yang benar-benar masuk daftar
    prioritas yang sama.

    `selection_rate` menunjukkan proporsi tiap kelompok yang terpilih; timpang
    tidaknya angka itu adalah inti dari analisis ini.

    Disebut *sensitivity analysis pada simulasi*, BUKAN bukti fairness pada
    populasi nyata. Irisan dengan n < `min_n` ditandai, karena metrik pada
    kelompok kecil sangat bervariasi.
    """
    y = pd.Series(np.asarray(y_true, dtype=float)).reset_index(drop=True)
    s = pd.Series(np.asarray(y_score, dtype=float)).reset_index(drop=True)
    sl = slices.reset_index(drop=True)
    chosen = (None if selected is None
              else pd.Series(np.asarray(selected, dtype=bool)).reset_index(drop=True))

    rows = []
    for col in sl.columns:
        for value, idx in sl.groupby(col, observed=True).groups.items():
            pos = list(idx)
            yi, si = y.iloc[pos], s.iloc[pos]
            valid = yi.notna() & si.notna()
            yi, si = yi[valid], si[valid]
            n = len(yi)
            if n == 0:
                continue

            row = {
                "slice": col, "value": str(value), "n": n,
                "underpowered": n < min_n,
                "prevalence": round(float(yi.mean()), 4),
            }
            row["auprc"] = (round(float(average_precision_score(yi, si)), 4)
                            if 0 < yi.sum() < n else float("nan"))

            if chosen is not None:
                ci = chosen.iloc[pos][valid]
                n_pos = int(yi.sum())
                row["recall_at_global_capacity"] = (
                    round(float(((yi == 1) & ci).sum() / n_pos), 4) if n_pos > 0 else float("nan")
                )
                row["selection_rate"] = round(float(ci.mean()), 4)
            rows.append(row)
    return pd.DataFrame(rows)


def error_analysis(
    y_true, y_score, features: pd.DataFrame, *,
    k_frac: float = 0.20, tie_break=None
) -> pd.DataFrame:
    """Karakteristik false negative vs true positive (TAB-07).

    False negative adalah kesalahan yang paling merugikan di sini: anak yang
    akan memburuk tetapi tidak masuk daftar prioritas. Paper harus menjelaskan
    siapa mereka, bukan hanya berapa banyak.
    """
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(y_score, dtype=float)
    valid = np.isfinite(y) & np.isfinite(s)
    # Titik operasi sama persis dengan metrik @K -- daftar prioritasnya identik.
    pred = np.zeros(len(s), dtype=bool)
    tb = None if tie_break is None else np.asarray(tie_break)[valid]
    pred[valid] = capacity_predictions(s[valid], k_frac, tb).astype(bool)

    groups = {
        "true_positive": valid & (y == 1) & pred,
        "false_negative": valid & (y == 1) & ~pred,
        "false_positive": valid & (y == 0) & pred,
        "true_negative": valid & (y == 0) & ~pred,
    }
    num = features.select_dtypes(include=[np.number])
    rows = []
    for name, mask in groups.items():
        row = {"group": name, "n": int(mask.sum())}
        if mask.any():
            row.update(num[mask].mean().round(3).to_dict())
        rows.append(row)
    return pd.DataFrame(rows)
