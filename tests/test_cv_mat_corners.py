"""Test deteksi alas polos tanpa marker (Opsi 1 / DEC-015)."""

import cv2
import numpy as np
import pytest

from cv.aruco import apply_homography
from cv.mat_corners import detect_mat_corners
from cv.pipeline import measure_length
from cv.quality import ImageQC
from cv.segment import ColorSegmenter

from _cv_synth import SPEC, STANDARD_MAT_COLOR, synth_plain_mat, synth_plain_mat_with_body


def test_alas_polos_terdeteksi_dengan_homografi_akurat():
    img, ppc, (x0, y0, x1, y1) = synth_plain_mat()
    det = detect_mat_corners(img, SPEC)
    assert det.ok, det.reason
    expected = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)
    assert np.allclose(det.image_points, expected, atol=3.0)


def test_urutan_sudut_konsisten_dengan_object_points():
    img, _, _ = synth_plain_mat()
    det = detect_mat_corners(img, SPEC)
    assert det.ok
    mapped = apply_homography(det.homography, det.image_points)
    # object_points: [(0,0), (w,0), (w,h), (0,h)] -> urutan TL, TR, BR, BL.
    assert np.allclose(mapped, SPEC.object_points(), atol=0.5)


def test_citra_tanpa_alas_ditolak():
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 255, (400, 500, 3), dtype=np.uint8)
    det = detect_mat_corners(noise, SPEC)
    assert not det.ok and "alas" in det.reason


def test_latar_belakang_menyentuh_tepi_tidak_dianggap_alas():
    # Alas penuh 1 bingkai (menyentuh tepi) = latar, bukan alas -> ditolak.
    img = np.full((400, 500, 3), STANDARD_MAT_COLOR, np.uint8)
    det = detect_mat_corners(img, SPEC)
    assert not det.ok


def test_pipeline_mengukur_panjang_dengan_alas_polos():
    img, _, _, body_cm = synth_plain_mat_with_body()
    res = measure_length(
        img, SPEC,
        segmenter=ColorSegmenter(mat_color=STANDARD_MAT_COLOR),
        image_qc=ImageQC(min_blur_var=1.0),
    )
    assert res.ok, res.qc_reasons
    assert res.length_cm == pytest.approx(body_cm, abs=1.5)
    assert res.model == "color"


def test_mode_marker_masih_tersedia():
    from cv.aruco import detect_markers

    from _cv_synth import synth_mat_with_body

    img, _, _, body_cm = synth_mat_with_body()
    res = measure_length(
        img, SPEC, detector=detect_markers,
        segmenter=ColorSegmenter(),
        image_qc=ImageQC(min_blur_var=1.0),
    )
    assert res.ok and res.length_cm == pytest.approx(body_cm, abs=1.5)


def test_pengukuran_tahan_foto_diputar_90_derajat():
    img, _, _, body_cm = synth_plain_mat_with_body()
    rotated = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    res = measure_length(
        rotated, SPEC,
        segmenter=ColorSegmenter(mat_color=STANDARD_MAT_COLOR),
        image_qc=ImageQC(min_blur_var=1.0),
    )
    assert res.ok, res.qc_reasons
    assert res.length_cm == pytest.approx(body_cm, abs=1.5)


def test_segiempat_berpola_ditolak():
    # Karpet/meja berpola (kotak-kotak) bukan alas polos -> ditolak.
    img = np.full((420, 520, 3), 230, np.uint8)
    x0, y0, x1, y1 = 60, 80, 60 + 240, 80 + 320
    for y in range(y0, y1, 20):
        for x in range(x0, x1, 20):
            color = 30 if ((x - x0) // 20 + (y - y0) // 20) % 2 == 0 else 220
            img[y:y + 20, x:x + 20] = color
    det = detect_mat_corners(img, SPEC)
    assert not det.ok


def test_segiempat_bujur_sangkar_ditolak():
    # Alas produk 60x100; kandidat bujur sangkar tidak cocok rasio -> ditolak.
    img = np.full((420, 520, 3), 230, np.uint8)
    img[80:320, 60:300] = (200, 120, 40)  # 240x240 px
    det = detect_mat_corners(img, SPEC)
    assert not det.ok


def test_deteksi_deterministik_antar_panggilan():
    img, _, _ = synth_plain_mat()
    a = detect_mat_corners(img, SPEC)
    b = detect_mat_corners(img, SPEC)
    assert a.ok and b.ok
    assert np.allclose(a.image_points, b.image_points, atol=1e-6)


def test_segiempat_seragam_warna_salah_ditolak():
    # Fail-closed dengan signature warna produk (DEC-015): segiempat
    # seragam beraspek 60:100 tapi bukan warna alas -> ditolak.
    from cv.mat_corners import PRODUCT_MAT_COLOR

    img = np.full((440, 520, 3), 230, np.uint8)
    img[20:420, 60:300] = (60, 140, 60)  # hijau seragam, 400x240 px = rasio 1.67
    assert not detect_mat_corners(img, SPEC, mat_color=PRODUCT_MAT_COLOR).ok
    # Tanpa signature warna: kandidat seragam lolos (batas protokol, DEC-015).
    assert detect_mat_corners(img, SPEC).ok


def test_pola_di_tepi_alas_ditolak():
    # Alas seragam tapi tepi dalamnya berpola -> ring tidak seragam -> ditolak.
    img = np.full((440, 520, 3), 230, np.uint8)
    img[40:400, 80:460] = (200, 120, 40)          # "alas"
    img[52:388, 92:448] = (90, 90, 90)            # bingkai gelap di tepi dalam
    assert not detect_mat_corners(img, SPEC).ok
