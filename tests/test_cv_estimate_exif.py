"""Test helper focal panjang dari EXIF (foto HP asli)."""

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
