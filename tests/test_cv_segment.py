"""Test segmentasi (V4): baseline warna + endpoint siluet (tanpa model berat)."""

import cv2
import numpy as np
import pytest

from cv.segment import ColorSegmenter, endpoints_from_mask, get_segmenter

from _cv_synth import synth_mat_with_body


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
    # Badan kecil di pojok alas: komponen terbesar tetap badan, bukan marker.
    img, ppc, box, _ = synth_mat_with_body(body_axes_cm=(20.0, 8.0))
    x0, y0, x1, y1 = box
    # Marker tetap di sudut; badan elips kecil di pojok kiri-bawah.
    img2 = img.copy()
    cv2.ellipse(img2, (x0 + int(12 * ppc), y1 - int(10 * ppc)),
                (int(10 * ppc), int(4 * ppc)), 0, 0, 360, (30, 120, 200), -1)
    res = ColorSegmenter().segment(img2)
    assert res.ok
    # Komponen terbesar harus badan (bukan marker): mask lebih dekat ke badan.
    ys, xs = np.nonzero(res.mask)
    cy = (ys.min() + ys.max()) / 2
    assert cy > (y0 + y1) / 2  # berada di bawah tengah alas, dekat badan kecil
