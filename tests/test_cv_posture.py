"""Test QC postur siluet (V5a, non-AI)."""

import numpy as np

from cv.posture import SilhouettePostureQC

QC = SilhouettePostureQC()


def _hrect(w, h, thickness=60):
    """Siluet persegi panjang horizontal lurus."""
    mask = np.zeros((h, w), bool)
    y0 = (h - thickness) // 2
    mask[y0:y0 + thickness, :] = True
    return mask


def test_siluet_lurus_lolos():
    res = QC.check(_hrect(400, 200))
    assert res["passed"], res["reasons"]
    assert res["aspect_ratio"] > 3.0 and res["bbox_fill"] > 0.9


def test_siluet_melengkung_ditandai():
    # Badan melengkung kuat: sumbu mengikuti 240*sin(pi*x/600) -> deviasi dari
    # chord 240/600 = 0.4 -> ~22 derajat > ambang 20.
    mask = np.zeros((360, 600), bool)
    for x in range(600):
        y = 50 + int(240 * np.sin(np.pi * x / 600))
        mask[y:y + 30, x] = True
    res = QC.check(mask)
    assert any("melengkung" in r for r in res["reasons"])


def test_tungkai_terpisah_ditandai():
    mask = np.zeros((300, 200), bool)
    mask[10:290, 60:140] = True    # badan atas sempit
    mask[250:290, 20:180] = True   # kaki melebar di bawah
    res = QC.check(mask)
    assert any("tungkai" in r for r in res["reasons"])


def test_siluet_terlalu_kecil_ditolak():
    res = QC.check(np.zeros((10, 10), bool))
    assert not res["passed"] and any("terlalu kecil" in r for r in res["reasons"])


def test_metrik_tidak_bergantung_posisi_di_bingkai():
    # Tubuh lurus di pojok bingkai besar: bbox-normalisasi -> tetap lolos.
    frame = np.zeros((900, 1400), bool)
    frame[60:200, 1000:1300] = _hrect(300, 140)  # badan horizontal kecil
    res = QC.check(frame)
    assert res["passed"], res["reasons"]
