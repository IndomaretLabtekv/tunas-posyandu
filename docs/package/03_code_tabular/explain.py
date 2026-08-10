"""Atribusi SHAP per anak (T8, TAB-09).

SHAP menunjukkan **kontribusi fitur terhadap keluaran model**. Ia bukan
penjelasan sebab-akibat dan bukan penjelasan medis: fitur dengan kontribusi
besar tidak berarti fitur itu menyebabkan anak memburuk. Antarmuka wajib
menyajikannya sebagai "faktor yang paling memengaruhi skor", disertai
keterangan tersebut (RESPONSIBLE_AI bagian 5).

Dua keluaran yang dipakai produk:

    explain_child()    3-5 faktor teratas untuk SATU anak -> halaman detail
    global_importance()  ranking fitur agregat -> paper 4.2 / Lampiran C

Label fitur sengaja ditulis dalam bahasa yang dapat dibaca petugas gizi, bukan
nama kolom. Kader dan petugas tidak perlu tahu apa itu `haz_slope_per_month`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Label yang tampil di UI. Nama kolom teknis tidak pernah dilihat pengguna.
FEATURE_LABELS = {
    "age_days": "Usia anak",
    "sex_is_male": "Jenis kelamin",
    "haz_t": "Status panjang badan saat ini",
    "length_cm_t": "Panjang badan terukur",
    "weight_kg_t": "Berat badan terukur",
    "haz_missing_t": "Hasil ukur tidak tersedia",
    "measured_by_cv_t": "Pengukuran memakai kamera",
    "n_prior_visits": "Jumlah kunjungan sebelumnya",
    "days_since_first_visit": "Lama sejak kunjungan pertama",
    "visit_gap_days_t": "Jarak dari kunjungan terakhir",
    "visit_gap_mean": "Rata-rata jarak antar kunjungan",
    "haz_slope_per_month": "Kecepatan perubahan pertumbuhan",
    "haz_delta_1visit": "Perubahan sejak kunjungan lalu",
    "haz_delta_3months": "Perubahan dalam 3 bulan terakhir",
    "haz_min_to_date": "Titik terendah pertumbuhan",
    "haz_max_to_date": "Titik tertinggi pertumbuhan",
    "haz_range_to_date": "Rentang naik-turun pertumbuhan",
    "haz_std_to_date": "Kestabilan pertumbuhan",
    "n_consecutive_declines": "Penurunan berturut-turut",
    "ever_stunted_to_date": "Pernah berstatus pendek",
    "months_since_haz_peak": "Lama sejak pertumbuhan terbaik",
    "length_velocity_cm_per_month": "Pertambahan panjang per bulan",
    "ses_index": "Kondisi sosial ekonomi keluarga",
    "birth_weight_kg": "Berat badan lahir",
    "immunization_on_schedule_t": "Imunisasi sesuai usia",
    "immunization_on_schedule_rate_to_date": "Keteraturan imunisasi",
    "exclusive_bf_known": "Status ASI eksklusif diketahui",
    "exclusive_bf_positive": "ASI eksklusif terpenuhi",
}


def label_for(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature)


DISPLAY_DECIMALS = 4


def displayed_shap(value: float) -> float:
    """Nilai SHAP sebagaimana ditampilkan di CSV/UI.

    Arah WAJIB dihitung dari nilai ini, bukan dari nilai mentah. Kalau tidak,
    kontribusi 0.00004 tampil sebagai `0.0` di CSV tetapi diberi arah
    "menaikkan" -- baris yang membantah dirinya sendiri.
    """
    return round(float(value), DISPLAY_DECIMALS)


def direction_for(value: float, atol: float = 1e-12) -> str:
    """Arah kontribusi. Nol berarti NETRAL, bukan menurunkan.

    Kontribusi tepat nol wajar terjadi: fitur yang tidak dipakai satu pun
    pohon, model kecil, atau `top_k` melebihi jumlah fitur berkontribusi.
    Menyebutnya "menurunkan" salah secara semantik dan langsung terbaca
    pengguna di dashboard.
    """
    if np.isclose(value, 0.0, atol=atol):
        return "netral"
    return "menaikkan" if value > 0 else "menurunkan"


@dataclass(frozen=True)
class Attribution:
    feature: str
    label: str
    value: float          # nilai fitur pada anak ini
    shap_value: float     # kontribusi terhadap skor
    direction: str        # "menaikkan" | "menurunkan" | "netral"

    def as_dict(self) -> dict:
        return {
            "feature": self.feature,
            "label": self.label,
            "value": None if pd.isna(self.value) else round(float(self.value), 3),
            "shap_value": displayed_shap(self.shap_value),
            "direction": self.direction,
        }


class Explainer:
    """Pembungkus SHAP TreeExplainer untuk model LightGBM biner.

    Nilai SHAP dihitung pada skala log-odds (keluaran mentah model), bukan
    probabilitas. Konsekuensinya: kontribusi TIDAK dapat dijumlahkan menjadi
    "berapa persen risiko" -- yang sah dibaca hanya arah dan urutan besarnya.
    """

    def __init__(self, model, feature_names: list[str]):
        try:
            import shap
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Butuh paket `shap`. Tambahkan ke requirements.txt lalu "
                "`pip install shap`."
            ) from exc
        self.model = model
        self.feature_names = list(feature_names)
        self._explainer = shap.TreeExplainer(model)

    def shap_values(self, X: pd.DataFrame) -> np.ndarray:
        """Matriks (n_baris x n_fitur) pada skala log-odds."""
        missing = set(self.feature_names) - set(X.columns)
        if missing:
            raise ValueError(f"Kolom fitur hilang: {sorted(missing)}")
        vals = self._explainer.shap_values(X[self.feature_names])
        if isinstance(vals, list):          # sebagian versi shap: satu array per kelas
            vals = vals[1]
        vals = np.asarray(vals)
        if vals.ndim == 3:                  # (n, f, kelas)
            vals = vals[:, :, 1]
        return vals

    def explain_child(self, X: pd.DataFrame, row_index, top_k: int = 5) -> list[Attribution]:
        """Faktor teratas untuk satu anak. Dipakai halaman detail dashboard."""
        if row_index not in X.index:
            raise KeyError(f"Baris {row_index!r} tidak ada.")
        row = X.loc[[row_index]]
        vals = self.shap_values(row)[0]
        order = np.argsort(-np.abs(vals))[:top_k]
        out = []
        for j in order:
            name = self.feature_names[j]
            shown = displayed_shap(vals[j])
            out.append(Attribution(
                feature=name,
                label=label_for(name),
                value=row[name].iloc[0],
                shap_value=shown,
                direction=direction_for(shown, atol=0.0),
            ))
        return out

    def explain_batch(self, X: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
        """Faktor teratas untuk banyak anak sekaligus (satu baris per faktor)."""
        vals = self.shap_values(X)
        rows = []
        for i, idx in enumerate(X.index):
            order = np.argsort(-np.abs(vals[i]))[:top_k]
            for rank, j in enumerate(order, start=1):
                name = self.feature_names[j]
                shown = displayed_shap(vals[i, j])
                rows.append({
                    "row_index": idx,
                    "rank": rank,
                    "feature": name,
                    "label": label_for(name),
                    "value": X[name].iloc[i],
                    "shap_value": shown,
                    "direction": direction_for(shown, atol=0.0),
                })
        return pd.DataFrame(rows)

    def global_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Rata-rata |SHAP| per fitur. Untuk paper, bukan untuk UI per anak."""
        vals = np.abs(self.shap_values(X)).mean(axis=0)
        df = pd.DataFrame({
            "feature": self.feature_names,
            "label": [label_for(f) for f in self.feature_names],
            "mean_abs_shap": np.round(vals, 5),
        })
        return df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def to_sentences(attributions: list[Attribution]) -> list[str]:
    """Ubah atribusi menjadi kalimat siap tampil di dashboard.

    Bahasanya sengaja netral -- "memengaruhi skor", bukan "menyebabkan".
    """
    out = []
    for a in attributions:
        if a.direction == "netral":
            out.append(f"{a.label} tidak mengubah skor prioritas anak ini.")
        else:
            out.append(f"{a.label} {a.direction} prioritas anak ini.")
    return out


DISCLAIMER = (
    "Faktor di atas menunjukkan apa yang paling memengaruhi skor prioritas "
    "sistem, bukan penyebab kondisi anak. Keputusan tindak lanjut tetap berada "
    "pada tenaga kesehatan."
)
