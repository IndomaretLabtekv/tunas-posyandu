"""Test segmentasi (V4): baseline warna + endpoint siluet (tanpa model berat)."""

import cv2
import numpy as np
import pytest

from cv.segment import ColorSegmenter, endpoints_from_mask, get_segmenter

from _cv_synth import synth_mat, synth_mat_with_body


def test_color_segmenter_menemukan_badan_elips():
    img, _, _, body_cm = synth_mat_with_body()
    res = ColorSegmenter().segment(img)
    assert res.ok and res.model == "color"
    fill = res.mask.mean()
    # Elips 45x12 cm pada alas 60x100 cm -> ~9% luasan; toleransi longgar.
    assert 0.03 < fill < 0.30


def test_endpoints_sesuai_ekstrem_elips():
    img, ppc, _, body_cm = synth_mat_with_body()
    res = ColorSegmenter().segment(img)
    ends = endpoints_from_mask(res.mask)
    assert ends is not None
    (x1, y1), (x2, y2) = ends
    # Sumbu panjang horizontal: jarak endpoint ~ panjang badan dalam piksel.
    span = np.hypot(x2 - x1, y2 - y1)
    assert span == pytest.approx(body_cm * ppc, rel=0.08)


def test_endpoints_mask_kosong_mengembalikan_none():
    assert endpoints_from_mask(np.zeros((100, 100), bool)) is None


def test_segmenter_registry():
    assert get_segmenter("color").model_name == "color"
    with pytest.raises(ValueError):
        get_segmenter("tidak-ada")


def test_badan_kecil_off_center_tetap_terpilih():
    # Hanya satu badan kecil di pojok kiri-bawah alas (tanpa badan di tengah):
    # komponen terbesar harus badan itu, bukan marker (DEC-014 baseline).
    img, ppc, box = synth_mat()  # alas marker, tanpa badan
    x0, y0, x1, y1 = box
    img2 = img.copy()
    cv2.ellipse(img2, (x0 + int(16 * ppc), y1 - int(12 * ppc)),
                (int(15 * ppc), int(6 * ppc)), 0, 0, 360, (30, 120, 200), -1)
    res = ColorSegmenter().segment(img2)
    assert res.ok
    ys, xs = np.nonzero(res.mask)
    cx_m, cy_m = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    # Centroid mask harus di kuadran kiri-bawah alas (tempat badan kecil).
    assert cx_m < (x0 + x1) / 2 - 5 * ppc
    assert cy_m > (y0 + y1) / 2 + 5 * ppc
