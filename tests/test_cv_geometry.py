"""Verifikasi ArUco, homografi, dan analisis plane-offset (CV-00..CV-04)."""

import cv2
import numpy as np
import pandas as pd
import pytest

from cv.aruco import (
    MatSpec,
    apply_homography,
    detect_markers,
    distance_cm,
    generate_marker_sheet,
    rectify,
)
from cv.geometry import (
    GeometryQC,
    camera_tilt_deg,
    expected_bias_cm,
    measure_length_cm,
    min_camera_height_for_tolerance,
    off_center_fraction,
    scale_error_factor,
)

SPEC = MatSpec(width_cm=60.0, height_cm=100.0)


def synth_mat(spec=SPEC, px_per_cm=8, margin=60, warp=None, marker_cm=8.0):
    """Bangun citra alas sintetis dengan 4 marker pada posisi diketahui."""
    w = int(spec.width_cm * px_per_cm) + 2 * margin
    h = int(spec.height_cm * px_per_cm) + 2 * margin
    img = np.full((h, w, 3), 255, np.uint8)
    mk = int(marker_cm * px_per_cm)
    sheet = generate_marker_sheet(spec, mk)

    # Sudut LUAR tiap marker harus jatuh tepat pada sudut alas.
    x0, y0 = margin, margin
    x1, y1 = margin + int(spec.width_cm * px_per_cm), margin + int(spec.height_cm * px_per_cm)
    placements = {
        0: (x0, y0),                 # sudut luar = kiri-atas marker
        1: (x1 - mk, y0),            # sudut luar = kanan-atas
        2: (x1 - mk, y1 - mk),       # sudut luar = kanan-bawah
        3: (x0, y1 - mk),            # sudut luar = kiri-bawah
    }
    for mid, (px, py) in placements.items():
        img[py:py + mk, px:px + mk] = cv2.cvtColor(sheet[mid], cv2.COLOR_GRAY2BGR)

    if warp is not None:
        img = cv2.warpPerspective(img, warp, (w, h), borderValue=(255, 255, 255))
    return img, px_per_cm, (x0, y0, x1, y1)


@pytest.fixture(scope="module")
def flat():
    img, ppc, box = synth_mat()
    return img, ppc, box, detect_markers(img, SPEC)


# ---------------------------------------------------------------- deteksi

def test_keempat_marker_terdeteksi(flat):
    _, _, _, det = flat
    assert det.ok and sorted(det.found_ids) == [0, 1, 2, 3]


def test_marker_hilang_ditolak_dengan_alasan_jelas():
    img, _, _ = synth_mat()
    img[:200, :] = 255                       # hapus dua marker atas
    det = detect_markers(img, SPEC)
    assert not det.ok
    assert "tidak lengkap" in det.reason or "tidak ada marker" in det.reason
    assert set(det.missing_ids) & {0, 1}


def test_citra_kosong_tidak_membuat_crash():
    det = detect_markers(np.zeros((10, 10, 3), np.uint8), SPEC)
    assert not det.ok and det.reason


def test_reprojection_error_kecil_pada_alas_datar(flat):
    _, _, _, det = flat
    assert det.reprojection_error_px < 2.0


# ---------------------------------------------------------------- homografi

def test_sudut_alas_terpetakan_ke_ukuran_fisik(flat):
    _, _, _, det = flat
    corners = apply_homography(det.homography, det.image_points)
    expected = SPEC.object_points()
    assert np.allclose(corners, expected, atol=0.5)


def test_pengukuran_pada_bidang_alas_akurat(flat):
    img, ppc, (x0, y0, x1, y1), det = flat
    # Dua titik pada bidang alas berjarak 50 cm secara vertikal.
    p1 = (x0 + 20 * ppc, y0 + 10 * ppc)
    p2 = (x0 + 20 * ppc, y0 + 60 * ppc)
    assert distance_cm(det, p1, p2) == pytest.approx(50.0, abs=0.5)


def test_rectify_menghasilkan_ukuran_sesuai_skala(flat):
    img, _, _, det = flat
    out = rectify(img, det, SPEC, px_per_cm=5.0)
    assert out.shape[1] == 300 and out.shape[0] == 500


def test_deteksi_gagal_menolak_pengukuran():
    det = detect_markers(np.zeros((10, 10, 3), np.uint8), SPEC)
    with pytest.raises(ValueError, match="tidak valid"):
        distance_cm(det, (0, 0), (1, 1))


# ---------------------------------------------------------------- plane offset

def test_faktor_skala_sesuai_rumus_pinhole():
    assert scale_error_factor(100.0, 10.0) == pytest.approx(100 / 90)
    assert scale_error_factor(200.0, 10.0) == pytest.approx(200 / 190)


def test_galat_mengecil_saat_kamera_lebih_jauh():
    a = expected_bias_cm(70.0, 100.0, 10.0)
    b = expected_bias_cm(70.0, 200.0, 10.0)
    assert a > b > 0


def test_galat_membesar_seiring_elevasi():
    vals = [expected_bias_cm(70.0, 150.0, z) for z in (0, 5, 10, 15)]
    assert vals[0] == 0.0
    assert all(np.diff(vals) > 0)


def test_elevasi_sepuluh_cm_pada_kamera_satu_meter_menghasilkan_galat_besar():
    """Angka inilah yang membuat DEC-005 dibuat bersyarat pada CV-00."""
    bias = expected_bias_cm(70.0, 100.0, 10.0)
    assert bias > 5.0, f"galat {bias:.1f} cm -- jauh di atas toleransi 1 cm"


def test_elevasi_tidak_valid_ditolak():
    for h, z in ((0, 5), (100, -1), (100, 100), (100, 150)):
        with pytest.raises(ValueError):
            scale_error_factor(h, z)


def test_tinggi_kamera_minimum_memenuhi_toleransi():
    h = min_camera_height_for_tolerance(object_elevation_cm=8.0, true_length_cm=70.0,
                                        tolerance_cm=1.0)
    assert expected_bias_cm(70.0, h, 8.0) == pytest.approx(1.0, rel=0.05)


# ---------------------------------------------------------------- geometry QC

def test_alas_datar_lolos_qc(flat):
    _, _, _, det = flat
    assert GeometryQC().check(det, SPEC)["passed"]


def test_kemiringan_alas_datar_mendekati_nol(flat):
    _, _, _, det = flat
    assert camera_tilt_deg(det, SPEC) < 3.0


def test_citra_miring_ditolak_qc():
    img, _, _ = synth_mat()
    h, w = img.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[0, 0], [w, 0], [w * 0.72, h], [w * 0.28, h]])   # trapesium kuat
    warped = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h),
                                 borderValue=(255, 255, 255))
    det = detect_markers(warped, SPEC)
    if not det.ok:
        pytest.skip("marker tidak terdeteksi pada distorsi ekstrem")
    res = GeometryQC(max_tilt_deg=8.0).check(det, SPEC)
    assert not res["passed"] and any("miring" in r for r in res["reasons"])


def test_tinggi_kamera_di_bawah_minimum_ditolak(flat):
    _, _, _, det = flat
    qc = GeometryQC(min_camera_height_cm=150.0)
    res = qc.check(det, SPEC, camera_height_cm=100.0)
    assert not res["passed"] and any("terlalu dekat" in r for r in res["reasons"])


def test_tinggi_kamera_tidak_diketahui_ditolak_bila_disyaratkan(flat):
    _, _, _, det = flat
    res = GeometryQC(min_camera_height_cm=150.0).check(det, SPEC, camera_height_cm=None)
    assert not res["passed"]


def test_posisi_pusat_bingkai_lebih_kecil_daripada_tepi(flat):
    img, _, _, det = flat
    h, w = img.shape[:2]
    assert off_center_fraction(det, (w / 2, h / 2), img.shape) < 0.05
    assert off_center_fraction(det, (5, 5), img.shape) > 0.9


# ---------------------------------------------------------------- runner

def test_ringkasan_melaporkan_coverage_bersama_mae():
    from cv.evaluate import summarize
    res = pd.DataFrame({
        "detected": [True, True, True, False],
        "qc_passed": [True, True, False, False],
        "abs_error_cm": [0.4, 0.6, np.nan, np.nan],
        "error_cm": [0.4, -0.6, np.nan, np.nan],
    })
    s = summarize(res)["value"]
    assert s["qc_pass_rate_coverage"] == 0.5
    assert s["mae_cm_on_accepted"] == pytest.approx(0.5)
    assert s["n_measured"] == 2


def test_keputusan_gerbang_menyebut_mitigasi_saat_gagal():
    from cv.evaluate import gate_decision, summarize
    res = pd.DataFrame({
        "detected": [True] * 4, "qc_passed": [True] * 4,
        "abs_error_cm": [4.0, 5.0, 6.0, 5.5], "error_cm": [4.0, 5.0, 6.0, 5.5],
    })
    msg = gate_decision(summarize(res), tolerance_cm=1.0)
    assert "TIDAK LULUS" in msg and "DEC-011" in msg


def test_keputusan_gerbang_lulus_saat_galat_kecil():
    from cv.evaluate import gate_decision, summarize
    res = pd.DataFrame({
        "detected": [True] * 4, "qc_passed": [True] * 4,
        "abs_error_cm": [0.3, 0.4, 0.2, 0.5], "error_cm": [0.3, -0.4, 0.2, 0.5],
    })
    assert "LULUS" in gate_decision(summarize(res), tolerance_cm=1.0)


def test_template_manifest_memuat_kolom_wajib():
    from cv.evaluate import MANIFEST_COLUMNS, manifest_template
    assert list(manifest_template().columns) == MANIFEST_COLUMNS
