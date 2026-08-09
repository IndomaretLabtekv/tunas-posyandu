"""Deteksi 4 sudut alas polos berukuran diketahui (Opsi 1, DEC-015).

Menggantikan marker ArUco sebagai referensi skala (V1): alas berwarna
seragam berukuran fisik diketahui (mis. 60x100 cm) dideteksi lewat
clustering warna, dipilih kontur segiempat terbesar yang tidak menyentuh
tepi bingkai, lalu 4 sudutnya di-refine subpiksel dan diurutkan konsisten
(TL, TR, BR, BL). Homografi dihitung identik dengan mode marker
(`cv/aruco.py`) -- yang berubah hanya cara menemukan 4 titik acuan.

Kontrak keluaran: `cv.aruco.DetectionResult`, sehingga seluruh modul hilir
(geometry/quality/segment/pipeline) TIDAK berubah.

Trade-off robustness (DEC-015): tanpa ID fidusial, deteksi lebih rapuh
terhadap cahaya, alas kusut, dan warna lantai yang mirip alas. Dikompensasi
dengan: kandidat wajib segiempat cembung di dalam bingkai, subpixel
refinement, dan QC framing/tilt di hilir. Mode marker tetap tersedia
sebagai comparator/fallback (DEC-015).
"""

from __future__ import annotations

import cv2
import numpy as np

from cv.aruco import DetectionResult, MatSpec, apply_homography

DEFAULT_MAX_DIM = 640        # ukuran kerja k-means; sudut di-refine di resolusi penuh
K_CLUSTERS = 4               # jumlah cluster warna
MIN_MAT_AREA_FRAC = 0.05     # alas minimal 5% luas bingkai
MIN_BORDER_MARGIN_FRAC = 0.02  # alas tidak boleh menyentuh tepi bingkai
POLY_EPS_FRAC = 0.02         # epsilon approxPolyDP


def detect_mat_corners(image: np.ndarray, spec: MatSpec,
                       max_dim: int = DEFAULT_MAX_DIM) -> DetectionResult:
    """Deteksi 4 sudut alas polos; hasil siap dipakai homografi.

    Gagal (ok=False + reason) bila: citra kosong, tidak ada kandidat
    segiempat cembung yang memenuhi syarat luas & margin bingkai, atau
    homografi tidak dapat dihitung.
    """
    if image is None or image.size == 0:
        return DetectionResult(reason="citra kosong")

    h, w = image.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    small = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))),
                       interpolation=cv2.INTER_AREA)

    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, _ = cv2.kmeans(pixels, K_CLUSTERS, None, criteria, 3,
                              cv2.KMEANS_PP_CENTERS)

    sh, sw = small.shape[:2]
    best: tuple[float, np.ndarray] | None = None
    for c in range(K_CLUSTERS):
        mask = (labels.reshape(sh, sw) == c).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_MAT_AREA_FRAC * sh * sw:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            m = MIN_BORDER_MARGIN_FRAC
            if bx < m * sw or by < m * sh or bx + bw > (1 - m) * sw \
                    or by + bh > (1 - m) * sh:
                continue  # menyentuh tepi = latar belakang, bukan alas
            peri = cv2.arcLength(cnt, True)
            if peri <= 0:
                continue
            approx = cv2.approxPolyDP(cnt, POLY_EPS_FRAC * peri, True)
            if len(approx) != 4 or not cv2.isContourConvex(approx):
                continue
            if best is None or area > best[0]:
                best = (area, approx.reshape(4, 2).astype(np.float64))

    if best is None:
        return DetectionResult(reason="alas tidak terdeteksi")

    pts = _refine_corners(image, best[1] / scale)
    ordered = _order_corners(pts)

    H, _ = cv2.findHomography(ordered, spec.object_points(), method=0)
    if H is None:
        return DetectionResult(reason="homografi gagal dihitung")

    det = DetectionResult(found_ids=[0, 1, 2, 3], image_points=ordered,
                          homography=H, ok=True, reason="")
    # Residual diagnostik (non-gating) -- sama seperti mode marker.
    back = apply_homography(np.linalg.inv(H), spec.object_points())
    det.reprojection_error_px = float(
        np.sqrt(((back - ordered) ** 2).sum(axis=1).mean()))
    return det


def _refine_corners(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Refinement subpiksel tiap sudut di resolusi penuh.

    Satu piksel galat sudut langsung menjadi galat milimeter pada hasil
    ukur (alas ~8 px/cm), jadi refinement ini bagian dari presisi.
    """
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
    refined = np.zeros_like(pts)
    for i, (x, y) in enumerate(pts):
        p = np.array([[[x, y]]], dtype=np.float32)
        refined[i] = cv2.cornerSubPix(gray, p, (7, 7), (-1, -1),
                                      criteria).reshape(2)
    return refined


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Urutkan 4 sudut konsisten: TL, TR, BR, BL (search jarum jam, y ke bawah).

    Urutan ini harus cocok dengan `MatSpec.object_points()`:
    [(0,0), (w,0), (w,h), (0,h)].
    """
    cx, cy = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx)
    pts = pts[np.argsort(angles)]           # naik: mulai dari kiri
    tl = int(np.argmin(pts[:, 0] + pts[:, 1]))
    return np.roll(pts, -tl, axis=0)
