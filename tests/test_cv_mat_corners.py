"""Test deteksi alas polos tanpa marker (Opsi 1 / DEC-015)."""

import cv2
import numpy as np
import pytest

from cv.aruco import MatSpec, apply_homography
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


def test_pola_tepi_ekstrem_ditolak_via_ring_chroma():
    # Pola tepi dengan lightness ekstrem (sangat gelap/terang): kroma LAB
    # memampat di L ekstrem sehingga jarak kroma cincin ring ke warna alas
    # melampaui ambang -> ditolak (fail-closed). Pola kroma-sama dengan
    # ayunan ringan memang tak terbedakan dari alas polos (batas protokol
    # DEC-015, diuji terpisah).
    img = np.full((440, 520, 3), 230, np.uint8)
    img[20:420, 60:300] = (200, 120, 40)
    def lightness_strip(y0, y1, x0, x1):
        for y in range(y0, y1):
            for x in range(x0, x1, 16):
                img[y, x:x + 8] = (40, 24, 8)
                img[y, x + 8:x + 16] = (255, 160, 55)
    lightness_strip(21, 29, 61, 299)
    lightness_strip(411, 419, 61, 299)
    lightness_strip(21, 419, 61, 69)
    lightness_strip(21, 419, 291, 299)
    assert not detect_mat_corners(img, SPEC, mat_color=STANDARD_MAT_COLOR).ok


def test_rotasi_berlawanan_dan_spec_terbalik():
    img, _, _, body_cm = synth_plain_mat_with_body()
    ccw = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    r = measure_length(ccw, SPEC,
                       segmenter=ColorSegmenter(mat_color=STANDARD_MAT_COLOR),
                       image_qc=ImageQC(min_blur_var=1.0))
    assert r.ok and r.length_cm == pytest.approx(body_cm, abs=1.5)

    # Spesifikasi width > height (100x60) juga harus rotation-safe.
    rev = MatSpec(width_cm=100.0, height_cm=60.0)
    det = detect_mat_corners(img, rev, mat_color=STANDARD_MAT_COLOR)
    assert det.ok, det.reason
    mapped = apply_homography(det.homography, det.image_points)
    assert np.allclose(mapped, rev.object_points(), atol=0.5)


def test_distractor_sewarna_jauh_tidak_ikut_tergabung():
    # Benda sewarna alas di tempat jauh: tidak boleh menyatu jadi quad palsu;
    # alas tetap terdeteksi sendiri.
    img, ppc, (x0, y0, x1, y1) = synth_plain_mat()
    # Kotak sewarna di area yang JAUH dari alas (tidak overlap, tidak
    # menyentuh tepi bingkai) -- harus tidak ikut tergabung.
    img[20:60, 545:585] = STANDARD_MAT_COLOR
    det = detect_mat_corners(img, SPEC, mat_color=STANDARD_MAT_COLOR)
    assert det.ok, det.reason
    expected = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)
    assert np.allclose(det.image_points, expected, atol=3.0)


def test_distractor_sewarna_jauh_dengan_frame_besar():
    # Frame besar: distractor sewarna di tempat yang BENAR-BENAR terpisah
    # (> kernel close & > pad bbox) -- tidak ikut tergabung (regresi r4).
    img = np.full((1200, 1200, 3), 230, np.uint8)
    img[100:1100, 250:850] = STANDARD_MAT_COLOR     # 600x1000 px = 60:100
    img[950:1000, 1050:1150] = STANDARD_MAT_COLOR   # distractor jauh
    det = detect_mat_corners(img, SPEC, mat_color=STANDARD_MAT_COLOR)
    assert det.ok, det.reason
    expected = np.array([[250, 100], [850, 100], [850, 1100], [250, 1100]],
                        dtype=np.float64)
    assert np.allclose(det.image_points, expected, atol=3.0)


def test_alas_terbelah_bayangan_tetap_tergabung():
    # Alas terbelah jadi 2 komponen oleh strip bayangan (kroma beda):
    # penggabungan spasial harus menyatukannya -> terdeteksi (regresi r4).
    img = np.full((440, 520, 3), 230, np.uint8)
    img[20:420, 60:300] = STANDARD_MAT_COLOR
    img[20:420, 175:185] = (90, 90, 90)              # strip bayangan 10px
    det = detect_mat_corners(img, SPEC, mat_color=STANDARD_MAT_COLOR)
    assert det.ok, det.reason
    expected = np.array([[60, 20], [300, 20], [300, 420], [60, 420]],
                        dtype=np.float64)
    assert np.allclose(det.image_points, expected, atol=3.0)


def test_plausible_mat_ring_chroma_langsung():
    # Unit test langsung _plausible_mat: quad bersih lolos; ring berpola
    # ekstrem ditolak oleh cek kroma ring.
    from cv.mat_corners import _plausible_mat

    img = np.full((440, 520, 3), 230, np.uint8)
    img[20:420, 60:300] = STANDARD_MAT_COLOR
    quad = np.array([[60, 20], [300, 20], [300, 420], [60, 420]], np.float64)
    assert _plausible_mat(img, quad, mat_color=STANDARD_MAT_COLOR)
    # Checker kontras tinggi menutupi ring: std luminansi ring > ambang.
    for y in range(21, 29):
        for x in range(61, 299, 16):
            img[y, x:x + 8] = (0, 0, 0)
            img[y, x + 8:x + 16] = (255, 255, 255)
    assert not _plausible_mat(img, quad, mat_color=STANDARD_MAT_COLOR)
