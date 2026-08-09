"""Test pipeline end-to-end (V6) pada citra alas sintetis, backend warna."""

import cv2
import numpy as np
import pytest

from cv.aruco import detect_markers
from cv.pipeline import measure_length
from cv.quality import ImageQC, blur_variance
from cv.segment import ColorSegmenter

from _cv_synth import SPEC, synth_mat_with_body


def _pipeline_kwargs(img):
    """ImageQC dengan ambang blur relatif terhadap citra uji (bukan absolut)."""
    sharp = blur_variance(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    return {"image_qc": ImageQC(min_blur_var=max(1.0, sharp / 2))}


def test_pipeline_mengukur_panjang_badan_elips():
    img, _, _, body_cm = synth_mat_with_body(body_axes_cm=(45.0, 12.0))
    res = measure_length(img, SPEC, segmenter=ColorSegmenter(), detector=detect_markers,
              **_pipeline_kwargs(img))
    assert res.ok, res.qc_reasons
    assert res.length_cm == pytest.approx(body_cm, abs=1.5)
    assert res.model == "color"
    assert 0.0 <= res.confidence <= 1.0
    assert res.endpoints_px is not None and len(res.endpoints_px) == 2
    assert res.haz is None  # tanpa haz_fn


def test_pipeline_menghitung_haz_bila_disediakan():
    img, _, _, _ = synth_mat_with_body()
    res = measure_length(
        img, SPEC, segmenter=ColorSegmenter(), detector=detect_markers,
        **_pipeline_kwargs(img), sex="M", age_days=300,
        haz_fn=lambda length_cm, sex, age_days: round(length_cm / 100, 3),
    )
    assert res.ok and res.haz is not None


def test_pipeline_menolak_citra_buram():
    img, _, _, _ = synth_mat_with_body()
    sharp = blur_variance(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    blurred = cv2.GaussianBlur(img, (15, 15), 0)
    res = measure_length(blurred, SPEC, segmenter=ColorSegmenter(),
                         detector=detect_markers,
                         image_qc=ImageQC(min_blur_var=sharp / 2))
    assert not res.ok


def test_pipeline_menolak_citra_tanpa_marker():
    img, _, _, _ = synth_mat_with_body()
    img[:, :] = 200  # hapus marker
    res = measure_length(img, SPEC, segmenter=ColorSegmenter(), detector=detect_markers,
              **_pipeline_kwargs(img))
    assert not res.ok


def test_postur_menurunkan_confidence_tanpa_menolak():
    # Badan gempal (aspect < 3): postur menandai, tetapi pengukuran tetap keluar.
    img, _, _, _ = synth_mat_with_body(body_axes_cm=(45.0, 22.0))
    res = measure_length(img, SPEC, segmenter=ColorSegmenter(), detector=detect_markers,
              **_pipeline_kwargs(img))
    assert res.ok
    assert res.confidence < 1.0
    assert any("aspek" in r or "pendek" in r or "melengkung" in r or
               "tungkai" in r or "tidak stabil" in r for r in res.qc_reasons)
