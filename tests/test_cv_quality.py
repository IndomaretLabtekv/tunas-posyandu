"""Test QC citra (V3): blur, framing, komposisi ImageQC."""

import cv2
import numpy as np
import pytest

from cv.quality import ImageQC, blur_variance
from cv.aruco import MatSpec, detect_markers

from _cv_synth import SPEC, synth_mat


def test_blur_variance_tajam_jauh_diatas_buram():
    img, _, _ = synth_mat()
    sharp = blur_variance(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    blurred = blur_variance(cv2.cvtColor(cv2.GaussianBlur(img, (15, 15), 0),
                                         cv2.COLOR_BGR2GRAY))
    assert sharp > blurred * 5


def test_imageqc_menolak_citra_buram():
    img, _, _ = synth_mat()
    sharp = blur_variance(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    det = detect_markers(img, SPEC)
    threshold = max(1.0, sharp / 2)
    res = ImageQC(min_blur_var=threshold).check(img, det, SPEC)
    assert res["passed"]

    blurred = cv2.GaussianBlur(img, (15, 15), 0)
    res = ImageQC(min_blur_var=threshold).check(blurred, det, SPEC)
    assert not res["passed"]
    assert any("buram" in r for r in res["reasons"])


def test_framing_menolak_marker_di_tepi_bingkai():
    img, _, _ = synth_mat()
    det = detect_markers(img, SPEC)
    assert det.ok
    # Simulasi framing buruk: geser titik marker ke tepi bingkai (pengambilan
    # asli dengan marker terpotong justru gagal deteksi -- itu jalur lain).
    h, w = img.shape[:2]
    det.image_points = det.image_points - np.array([w * 0.49, 0.0])
    res = ImageQC().check(img, det, SPEC)
    assert not res["passed"]
    assert any("terpotong" in r for r in res["reasons"])


def test_marker_tidak_terbaca_ditolak():
    img, _, _ = synth_mat()
    img[:200, :] = 255  # hapus dua marker atas
    det = detect_markers(img, SPEC)
    res = ImageQC().check(img, det, SPEC)
    assert not res["passed"]
