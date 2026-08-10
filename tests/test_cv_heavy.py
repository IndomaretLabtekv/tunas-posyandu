"""Test model berat (BiRefNet_dynamic, ViTPose) -- di-skip kecuali RUN_HEAVY=1.

Model ini butuh unduhan besar (BiRefNet ~445 MB) dan inference CPU lambat
(~10-60 detik/citra). Jalankan manual:  RUN_HEAVY=1 pytest tests/test_cv_heavy.py -q
"""

import os

import pytest

from _cv_synth import synth_mat_with_body

RUN_HEAVY = os.environ.get("RUN_HEAVY") == "1"

pytestmark = [
    pytest.mark.skipif(not RUN_HEAVY, reason="set RUN_HEAVY=1 untuk menjalankan"),
    pytest.mark.heavy,
]


def test_birefnet_mensegmentasi_badan_sintetis():
    from cv.segment import BiRefNetSegmenter

    img, _, _, _ = synth_mat_with_body()
    res = BiRefNetSegmenter().segment(img)
    assert res.ok, res.reason
    fill = res.mask.mean()
    assert 0.01 < fill < 0.40, f"fill={fill:.3f}"


def test_vitpose_tersedia_dan_menghasilkan_skor():
    from cv.posture import ViTPosePostureQC

    img, _, _, _ = synth_mat_with_body()
    qc = ViTPosePostureQC()
    assert qc.available(), qc._err
    out = qc.check(img)
    assert out is not None
    assert 0.0 <= out["mean_conf"] <= 1.0
