"""Test deteksi alas polos tanpa marker (Opsi 1 / DEC-015)."""

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
