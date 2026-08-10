"""Helper citra alas sintetis untuk test kanal visual (tanpa foto asli)."""

import cv2
import numpy as np

from cv.aruco import MatSpec, generate_marker_sheet

SPEC = MatSpec(width_cm=60.0, height_cm=100.0)


def synth_mat(spec=SPEC, px_per_cm=8, margin=60, marker_cm=8.0):
    """Bangun citra alas dengan 4 marker pada posisi diketahui."""
    w = int(spec.width_cm * px_per_cm) + 2 * margin
    h = int(spec.height_cm * px_per_cm) + 2 * margin
    img = np.full((h, w, 3), 255, np.uint8)
    mk = int(marker_cm * px_per_cm)
    sheet = generate_marker_sheet(spec, mk)

    x0, y0 = margin, margin
    x1, y1 = margin + int(spec.width_cm * px_per_cm), margin + int(spec.height_cm * px_per_cm)
    placements = {
        0: (x0, y0),
        1: (x1 - mk, y0),
        2: (x1 - mk, y1 - mk),
        3: (x0, y1 - mk),
    }
    for mid, (px, py) in placements.items():
        img[py:py + mk, px:px + mk] = cv2.cvtColor(sheet[mid], cv2.COLOR_GRAY2BGR)
    return img, px_per_cm, (x0, y0, x1, y1)


def synth_mat_with_body(body_color=(30, 120, 200), body_axes_cm=(45.0, 12.0),
                        px_per_cm=8):
    """Alas + badan elips PADA bidang alas (z=0), sumbu panjang horizontal.

    Mengembalikan (citra, px_per_cm, box, panjang_badan_cm).
    """
    img, ppc, box = synth_mat(px_per_cm=px_per_cm)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    axes = (int(body_axes_cm[0] * ppc / 2), int(body_axes_cm[1] * ppc / 2))
    cv2.ellipse(img, (cx, cy), axes, 0, 0, 360, body_color, -1)
    return img, ppc, box, body_axes_cm[0]


# --- Alas polos tanpa marker (Opsi 1 / DEC-015) -----------------------------

# Satu sumber kebenaran: warna alas standar produk didefinisikan di modul CV.
from cv.mat_corners import PRODUCT_MAT_COLOR as STANDARD_MAT_COLOR  # noqa: E402

FLOOR_COLOR = (230, 230, 230)


def synth_plain_mat(mat_color=STANDARD_MAT_COLOR, floor_color=FLOOR_COLOR,
                    spec=SPEC, px_per_cm=8, margin=60):
    """Alas polos warna seragam di atas lantai kontras (TANPA marker).

    Mengembalikan (citra, px_per_cm, box_alas).
    """
    w = int(spec.width_cm * px_per_cm) + 2 * margin
    h = int(spec.height_cm * px_per_cm) + 2 * margin
    img = np.full((h, w, 3), floor_color, np.uint8)
    x0, y0 = margin, margin
    x1, y1 = margin + int(spec.width_cm * px_per_cm), margin + int(spec.height_cm * px_per_cm)
    img[y0:y1, x0:x1] = mat_color
    return img, px_per_cm, (x0, y0, x1, y1)


def synth_plain_mat_with_body(body_color=(30, 120, 200), body_axes_cm=(45.0, 12.0),
                              mat_color=STANDARD_MAT_COLOR, px_per_cm=8):
    """Alas polos + badan elips di atasnya (markerless).

    Mengembalikan (citra, px_per_cm, box_alas, panjang_badan_cm).
    """
    img, ppc, box = synth_plain_mat(mat_color=mat_color, px_per_cm=px_per_cm)
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    axes = (int(body_axes_cm[0] * ppc / 2), int(body_axes_cm[1] * ppc / 2))
    cv2.ellipse(img, (cx, cy), axes, 0, 0, 360, body_color, -1)
    return img, ppc, box, body_axes_cm[0]
