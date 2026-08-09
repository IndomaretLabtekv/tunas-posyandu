"""Test fungsi murni runner eksperimen (parsing manifest)."""

import csv
from pathlib import Path

import pytest

from cv.aruco import MatSpec
from cv.mat_corners import PRODUCT_MAT_COLOR


@pytest.fixture()
def manifest_file(tmp_path):
    p = tmp_path / "manifest.csv"
    p.write_text(
        "image,mat_width_cm,mat_height_cm,mat_color_b,mat_color_g,mat_color_r\n"
        "Gaim_Yoga_Mat_1_2019-05-15.jpg,183,61,199,66,37\n"
        "tanpa_warna.jpg,60,100,,\n")
    return p


def test_manifest_diparse_bgr_dan_default(monkeypatch, manifest_file):
    import scripts.run_cv_experiments as runner
    monkeypatch.setattr(runner, "MANIFEST", manifest_file)
    cfg = runner._load_manifest()
    assert "Gaim_Yoga_Mat_1_2019-05-15.jpg" in cfg
    assert cfg["Gaim_Yoga_Mat_1_2019-05-15.jpg"]["spec"] == MatSpec(183.0, 61.0)
    # BGR: (199, 66, 37) -- bukan RGB (37, 66, 199).
    assert cfg["Gaim_Yoga_Mat_1_2019-05-15.jpg"]["mat_color"] == (199, 66, 37)
    assert cfg["tanpa_warna.jpg"]["mat_color"] is None


def test_manifest_tidak_ada_mengembalikan_kosong(monkeypatch, tmp_path):
    import scripts.run_cv_experiments as runner
    monkeypatch.setattr(runner, "MANIFEST", tmp_path / "tidak-ada.csv")
    assert runner._load_manifest() == {}
