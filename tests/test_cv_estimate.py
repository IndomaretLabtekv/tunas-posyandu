"""Test mode estimasi tanpa referensi (DEC-016) pada citra sintetis."""

import cv2
import numpy as np
import pytest

from cv.estimate import NEWBORN_HEAD_CM, estimate_length_no_reference

SKIN = (140, 170, 220)         # BGR kulit realistis (Cr~155, Cb~104 di YCrCb)
BLANKET = (200, 120, 60)       # BGR selimut biru


def synth_baby(ppc=8, body_cm=(40.0, 9.0), head_cm=NEWBORN_HEAD_CM,
               neck_cm=4.0):
    """Selimut + kepala bulat + leher sempit + badan elips, TANPA overlap.

    Kepala (11 cm) lebih lebar dari badan (9 cm) dan dipisahkan leher
    sempit -- supaya profil lebar kulit bisa memisahkan kepala.
    Total span = head + neck + body. Canvas cukup lebar untuk kepala
    raksasa. Mengembalikan (citra, panjang_total_cm, diameter_kepala_px).
    """
    h, w = 500, 1000
    img = np.full((h, w, 3), BLANKET, np.uint8)
    cy = h // 2
    head_r = int(head_cm * ppc / 2)
    hx = head_r + 20                       # pusat kepala (margin dari tepi)
    # Leher: persegi sempit di kanan kepala.
    neck_x0 = hx + head_r
    cv2.rectangle(img, (neck_x0, cy - int(2 * ppc)),
                  (neck_x0 + int(neck_cm * ppc), cy + int(2 * ppc)), SKIN, -1)
    # Badan: elips di kanan leher (tanpa overlap).
    bx = neck_x0 + int(neck_cm * ppc) + int(body_cm[0] * ppc / 2)
    cv2.ellipse(img, (bx, cy), (int(body_cm[0] * ppc / 2),
                                int(body_cm[1] * ppc / 2)), 0, 0, 360, SKIN, -1)
    # Kepala: lingkaran di ujung kiri.
    cv2.circle(img, (hx, cy), head_r, SKIN, -1)
    total_cm = head_cm + neck_cm + body_cm[0]
    return img, total_cm, head_cm * ppc


def test_estimasi_mendekati_panjang_sebenarnya():
    img, total_cm, head_px = synth_baby()
    r = estimate_length_no_reference(img)
    assert r.ok, r.reasons
    assert r.length_cm == pytest.approx(total_cm, rel=0.10)
    assert r.confidence == 0.3
    assert r.method == "head_prior"
    assert r.head_diameter_px == pytest.approx(head_px, rel=0.1)


def test_rasio_kepala_tidak_fisiologis_fallback_perspektif():
    # Kepala raksasa (rasio > 0.35) -> prior kepala ditolak -> perspektif.
    img, total_cm, _ = synth_baby(head_cm=25.0)
    r = estimate_length_no_reference(img, camera_height_cm=80.0, focal_px=640.0)
    assert r.ok, r.reasons
    assert r.method == "perspective_prior"
    # Skala pinhole: span_px * H / f = total_cm (ppc 8 -> f/H = 8).
    assert r.length_cm == pytest.approx(total_cm, rel=0.10)


def test_tanpa_foreground_gagal():
    img = np.full((200, 300, 3), BLANKET, np.uint8)  # selimut saja
    r = estimate_length_no_reference(img)
    assert not r.ok and r.reasons


def test_kepala_di_ujung_lain_tetap_terukur():
    # Mirror sintetis: kepala di sisi kanan (ujung proyeksi MAX). Scan arah
    # terbalik harus tetap menemukan kepala (regresi reviewer round-3).
    img, total_cm, head_px = synth_baby()
    flipped = img[:, ::-1].copy()
    r = estimate_length_no_reference(flipped)
    assert r.ok, r.reasons
    assert r.method == "head_prior", "kepala di ujung MAX harus terdeteksi"
    assert r.head_diameter_px == pytest.approx(head_px, rel=0.10)
    assert r.length_cm == pytest.approx(total_cm, rel=0.10)


def test_rasio_tepat_di_batas_atas_jatuh_ke_perspektif():
    # Rasio kepala:panjang ~0.32 (batas MAX) -> gate STRICT menolak.
    # Kepala 21 cm -> 21/(21+4+40) = 0.323 > 0.32.
    img, total_cm, _ = synth_baby(head_cm=21.0, body_cm=(40.0, 9.0))
    r = estimate_length_no_reference(img, camera_height_cm=80.0, focal_px=640.0)
    assert r.ok, r.reasons
    # Di atas batas fisiologis -> perspektif (bukan head_prior).
    assert r.method == "perspective_prior"


def test_parameter_perspektif_tidak_valid_ditolak():
    from _cv_synth import synth_plain_mat_with_body  # noqa: F401
    img, _, _ = synth_baby(head_cm=25.0)  # rasio non-fisiologis -> perspektif
    r = estimate_length_no_reference(img, camera_height_cm=0.0, focal_px=640.0)
    assert not r.ok
