"""Test helper focal panjang dari EXIF (foto HP asli)."""

import cv2
import numpy as np
import pytest

from PIL import Image

from cv.estimate import focal_px_from_exif


def _jpeg_with_focal(tmp_path, focal_35mm):
    p = tmp_path / "foto.jpg"
    img = Image.fromarray(np.full((100, 200, 3), 200, np.uint8))
    exif = Image.Exif()
    exif[0x9205] = focal_35mm          # FocalLength
    exif[0xA405] = focal_35mm          # FocalLengthIn35mmFilm
    img.save(p, exif=exif)
    return p


def test_focal_dari_exif(tmp_path):
    p = _jpeg_with_focal(tmp_path, 26)
    f = focal_px_from_exif(p, image_width_px=3000)
    assert f == pytest.approx(26 * 3000 / 36)   # ~2166


def test_tanpa_exif_mengembalikan_none(tmp_path):
    p = tmp_path / "polos.jpg"
    Image.fromarray(np.full((100, 100, 3), 200, np.uint8)).save(p)
    assert focal_px_from_exif(p, 1000) is None


def test_exif_rusak_atau_tidak_ada_mengembalikan_none(tmp_path):
    p = tmp_path / "rusak.jpg"
    p.write_bytes(b"bukan jpeg")
    assert focal_px_from_exif(p, 1000) is None
    assert focal_px_from_exif(tmp_path / "tidak-ada.jpg", 1000) is None


def test_measure_or_estimate_dua_mode():
    from cv.estimate import measure_or_estimate
    from cv.quality import ImageQC
    from cv.segment import ColorSegmenter

    from _cv_synth import STANDARD_MAT_COLOR, synth_plain_mat_with_body

    # Mode 1: dengan alas -> measurement.
    img, _, _, _ = synth_plain_mat_with_body()
    pr = measure_or_estimate(
        img, segmenter=ColorSegmenter(mat_color=STANDARD_MAT_COLOR),
        image_qc=ImageQC(min_blur_var=1.0))
    assert pr.mode == "measurement" and pr.length_cm is not None
    assert not pr.is_estimate

    # Mode 2: tanpa alas -> estimate (bukan rejected).
    img2 = np.full((400, 500, 3), (200, 120, 60), np.uint8)  # selimut saja
    cv2.circle(img2, (200, 200), 40, (140, 170, 220), -1)    # "kepala"
    cv2.ellipse(img2, (320, 220), (90, 30), 0, 0, 360, (140, 170, 220), -1)
    pr2 = measure_or_estimate(img2)
    assert pr2.mode == "estimate", "tanpa alas harus jatuh ke estimasi"
    assert pr2.estimate.ok and pr2.length_cm is not None
    assert any("pengukuran gagal" in r for r in pr2.estimate.reasons)
