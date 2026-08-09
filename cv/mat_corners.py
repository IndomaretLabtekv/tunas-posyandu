"""Deteksi 4 sudut alas polos berukuran diketahui (Opsi 1, DEC-015).

Menggantikan marker ArUco sebagai referensi skala (V1): alas berwarna
seragam berukuran fisik diketahui (mis. 60x100 cm) dideteksi lewat
clustering warna (k-means deterministik), dipilih kandidat segiempat
cembung terbesar yang tidak menyentuh tepi bingkai, lalu 4 sudutnya
di-refine subpiksel dan dilabel ulang agar konsisten dengan
`MatSpec.object_points()`.

Keandalan (fail-closed, DEC-015):
- Orientasi rotasi-invariant: sisi pendek/panjang quad dicocokkan dengan
  dimensi MatSpec, sehingga foto diputar 90 deg pun tetap terukur benar.
- Kandidat divalidasi: rasio sisi sesuai aspek alas, permukaan dalam
  relatif seragam (alas polos), tidak menyentuh tepi bingkai.
- Tanpa ID fidusial, verifikasi korespondensi sudut tidak ada; galat
  deteksi diukur di CV-01/CV-02, bukan diasumsikan.

Kontrak keluaran: `cv.aruco.DetectionResult`, sehingga seluruh modul
hilir (geometry/quality/segment/pipeline) TIDAK berubah. Mode marker
ArUco tetap tersedia sebagai comparator/fallback (DEC-015).
"""

from __future__ import annotations

import cv2
import numpy as np

from cv.aruco import DetectionResult, MatSpec, apply_homography

DEFAULT_MAX_DIM = 640          # ukuran kerja k-means; sudut di-refine di resolusi penuh
K_CLUSTERS = 4                 # jumlah cluster warna
MIN_MAT_AREA_FRAC = 0.05       # alas minimal 5% luas bingkai
MIN_BORDER_MARGIN_FRAC = 0.02  # alas tidak boleh menyentuh tepi bingkai
POLY_EPS_FRAC = 0.02           # epsilon approxPolyDP
MIN_SIDE_RATIO = 1.25          # rasio sisi panjang/pendek minimum (alas tidak bujur sangkar)
SIDE_RATIO_TOL = 1.35          # toleransi atas rasio sisi vs spesifikasi alas
MAX_RING_STD = 60.0            # std luminansi cincin dalam quad (permukaan seragam)
KMEANS_SEED = 7                # determinisme k-means (sklearn)


def detect_mat_corners(image: np.ndarray, spec: MatSpec,
                       max_dim: int = DEFAULT_MAX_DIM) -> DetectionResult:
    """Deteksi 4 sudut alas polos; hasil siap dipakai homografi.

    Gagal (ok=False + reason) bila: citra kosong, tidak ada kandidat
    segiempat cembung yang memenuhi syarat, kandidat tidak lolos validasi
    sisi/keseragaman, atau homografi tidak dapat dihitung.
    """
    if image is None or image.size == 0:
        return DetectionResult(reason="citra kosong")

    h, w = image.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    small = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))),
                       interpolation=cv2.INTER_AREA)

    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape(-1, 3).astype(np.float32)
    from sklearn.cluster import KMeans
    labels = KMeans(n_clusters=K_CLUSTERS, n_init=3,
                    random_state=KMEANS_SEED).fit_predict(pixels)

    sh, sw = small.shape[:2]
    candidates: list[tuple[float, np.ndarray]] = []
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
            candidates.append((area, approx.reshape(4, 2).astype(np.float64)))

    candidates.sort(key=lambda t: t[0], reverse=True)
    for _, quad in candidates:
        pts = _refine_corners(image, quad / scale)
        ordered = _orient_to_object(pts, spec)
        if ordered is None:
            continue
        if not _plausible_mat(image, ordered):
            continue
        H, _ = cv2.findHomography(ordered, spec.object_points(), method=0)
        if H is None:
            continue
        det = DetectionResult(found_ids=[0, 1, 2, 3], image_points=ordered,
                              homography=H, ok=True, reason="")
        # Residual diagnostik (non-gating) -- sama seperti mode marker.
        back = apply_homography(np.linalg.inv(H), spec.object_points())
        det.reprojection_error_px = float(
            np.sqrt(((back - ordered) ** 2).sum(axis=1).mean()))
        return det

    return DetectionResult(reason="alas tidak terdeteksi")


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


def _orient_to_object(pts: np.ndarray, spec: MatSpec) -> np.ndarray | None:
    """Label ulang sudut agar cocok dengan `MatSpec.object_points()`.

    `pts` diasumsikan urut siklik (dari pengurutan sudut centroid).
    Sisi pendek/panjang quad dicocokkan dengan dimensi alas, sehingga
    hasil TAHAN rotasi 90 deg. None bila rasio sisi tidak meyakinkan
    (bukan alas, atau foto sangat miring melebihi batas protokol).
    """
    s = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i])) for i in range(4)]
    pair_a = (s[0] + s[2]) / 2.0   # sisi pts0-pts1 dan pts2-pts3
    pair_b = (s[1] + s[3]) / 2.0   # sisi pts1-pts2 dan pts3-pts0
    lo, hi = sorted((pair_a, pair_b))
    exp = max(spec.width_cm, spec.height_cm) / min(spec.width_cm, spec.height_cm)
    if hi / lo < MIN_SIDE_RATIO or hi / lo > exp * SIDE_RATIO_TOL:
        return None
    if pair_a > pair_b:
        # Sisi pts0-pts1 = sisi panjang (h). Untuk object_points tetap
        # [(0,0),(w,0),(w,h),(0,h)], urutan pikselnya menjadi [0,3,2,1].
        return np.array([pts[0], pts[3], pts[2], pts[1]])
    return pts


def _plausible_mat(image: np.ndarray, pts: np.ndarray) -> bool:
    """Permukaan alas harus relatif seragam (cincin dalam quad).

    Menolak "segiempat apa pun" (meja berpola, jendela, karpet motif):
    alas produk polos, jadi deviasi luminansi pada cincin dekat tepi
    harus kecil. Tubuh di tengah tidak memengaruhi cincin ini.
    """
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.fillPoly(mask, [pts.astype(np.int32)], 255)
    eroded = cv2.erode(mask, np.ones((15, 15), np.uint8))
    ring = mask & ~eroded
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    vals = gray[ring > 0]
    return len(vals) >= 1000 and float(vals.std()) < MAX_RING_STD
