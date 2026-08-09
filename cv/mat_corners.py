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

DEFAULT_MAX_DIM = 640          # ukuran kerja; sudut di-refine di resolusi penuh
K_CLUSTERS = 4                 # jumlah cluster warna (jalur tanpa mat_color)
MIN_MAT_AREA_FRAC = 0.05       # alas minimal 5% luas bingkai
MIN_BORDER_MARGIN_FRAC = 0.02  # alas tidak boleh menyentuh tepi bingkai
POLY_EPS_FRAC = 0.02           # epsilon approxPolyDP
MIN_SIDE_RATIO = 1.25          # rasio sisi panjang/pendek minimum (alas tidak bujur sangkar)
SIDE_RATIO_TOL = 1.35          # toleransi atas rasio sisi vs spesifikasi alas
MAX_RING_STD = 60.0            # std luminansi cincin dalam quad (permukaan seragam)
MAX_RING_CHROMA_DIST = 40.0    # jarak kroma (a,b) cincin vs warna alas standar
KMEANS_SEED = 7                # determinisme k-means (sklearn)
KMEANS_MAX_ITER = 10           # clustering warna cukup 10 iterasi
CHROMA_THRESH = 35.0           # ambang jarak kroma LAB (jalur warna produk)
CLOSE_KERNEL = 15              # kernel morfologi penutup celah bayangan
MAX_MERGE_COMPONENTS = 3       # gabung hingga 3 komponen alas terbesar

# Spesifikasi alas standar produk (DEC-015). Satu-satunya "signature" fisik
# yang bisa memverifikasi bahwa quad yang ditemukan ADALAH alas produk.
PRODUCT_MAT_COLOR = (200, 120, 40)   # BGR
PRODUCT_MAT_SPEC = MatSpec(width_cm=60.0, height_cm=100.0)


def detect_mat_corners(image: np.ndarray, spec: MatSpec,
                       max_dim: int = DEFAULT_MAX_DIM,
                       mat_color: tuple[int, int, int] | None = None) -> DetectionResult:
    """Deteksi 4 sudut alas polos; hasil siap dipakai homografi.

    Dua jalur segmentasi:
    - `mat_color` diberikan (jalur produk): segmentasi jarak kroma LAB
      terhadap warna alas standar -- TAHAN gradien cahaya/bayangan yang
      memecah k-means; komponen terbesar digabung (hingga 3) untuk alas
      yang terbelah bayangan; cincin quad wajib berwarna mendekati warna
      alas (fail-closed penuh).
    - `mat_color=None` (generic): k-means mencari segiempat seragam;
      batas protokol ini didokumentasikan (DEC-015) -- kandidat seragam
      beraspek sama bisa lolos, dan gradien cahaya kuat dapat memecah
      cluster.

    Gagal (ok=False + reason) bila: citra kosong, tidak ada kandidat
    segiempat cembung yang memenuhi syarat, kandidat tidak lolos validasi
    sisi/warna/keseragaman, atau homografi tidak dapat dihitung.
    """
    if image is None or image.size == 0:
        return DetectionResult(reason="citra kosong")

    h, w = image.shape[:2]
    scale = min(1.0, max_dim / max(h, w))
    small = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))),
                       interpolation=cv2.INTER_AREA)

    if mat_color is not None:
        masks = _mat_masks_chroma(small, mat_color)
    else:
        masks = _mat_masks_kmeans(small)

    candidates: list[tuple[float, np.ndarray]] = []
    for mask in masks:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < MIN_MAT_AREA_FRAC * mask.shape[0] * mask.shape[1]:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            m = MIN_BORDER_MARGIN_FRAC
            if bx < m * mask.shape[1] or by < m * mask.shape[0] \
                    or bx + bw > (1 - m) * mask.shape[1] \
                    or by + bh > (1 - m) * mask.shape[0]:
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
        if not _plausible_mat(image, ordered, mat_color=mat_color):
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


def _mat_masks_chroma(small: np.ndarray, mat_color_bgr: tuple[int, int, int],
                      chroma_thresh: float = CHROMA_THRESH,
                      max_merge: int = MAX_MERGE_COMPONENTS) -> list[np.ndarray]:
    """Mask alas via jarak kroma LAB (a,b) -- invarian terhadap level cahaya.

    Mengembalikan daftar mask kandidat: komponen terbesar, lalu gabungan
    komponen terbesar 1+2, 1+2+3 (alas yang terbelah bayangan/gradien
    tetap bisa menyatu). Hanya kroma (a,b) yang dipakai, bukan lightness.
    """
    lab_img = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    target = cv2.cvtColor(np.uint8([[mat_color_bgr]]), cv2.COLOR_BGR2LAB)[0, 0, 1:]
    dist = np.linalg.norm(lab_img[:, :, 1:].astype(np.float32)
                          - target.astype(np.float32), axis=2)
    base = (dist <= chroma_thresh).astype(np.uint8) * 255
    base = cv2.morphologyEx(base, cv2.MORPH_CLOSE,
                            np.ones((CLOSE_KERNEL, CLOSE_KERNEL), np.uint8))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(base, 8)
    order = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])
    masks: list[np.ndarray] = []
    acc = np.zeros_like(base)
    for i in order[:max_merge]:
        acc[labels == i] = 255
        masks.append(acc.copy())
    return masks


def _mat_masks_kmeans(small: np.ndarray) -> list[np.ndarray]:
    """Jalur generic tanpa mat_color: mask per cluster k-means (LAB)."""
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    pixels = lab.reshape(-1, 3).astype(np.float32)
    from sklearn.cluster import KMeans
    labels = KMeans(n_clusters=K_CLUSTERS, n_init=3, max_iter=KMEANS_MAX_ITER,
                    random_state=KMEANS_SEED).fit_predict(pixels)
    sh, sw = small.shape[:2]
    return [(labels.reshape(sh, sw) == c).astype(np.uint8) * 255
            for c in range(K_CLUSTERS)]


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
    hasil TAHAN rotasi 90 deg, untuk spesifikasi width<height maupun
    sebaliknya. None bila rasio sisi tidak meyakinkan (bukan alas, atau
    foto sangat miring melebihi batas protokol).
    """
    s = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i])) for i in range(4)]
    pair_a = (s[0] + s[2]) / 2.0   # sisi pts0-pts1 dan pts2-pts3
    pair_b = (s[1] + s[3]) / 2.0   # sisi pts1-pts2 dan pts3-pts0
    lo, hi = sorted((pair_a, pair_b))
    exp = max(spec.width_cm, spec.height_cm) / min(spec.width_cm, spec.height_cm)
    if hi / lo < MIN_SIDE_RATIO or hi / lo > exp * SIDE_RATIO_TOL:
        return None
    # object_points: [(0,0),(w,0),(w,h),(0,h)] -> sisi pts0-pts1 = width.
    long_is_a = pair_a >= pair_b          # sisi pts0-pts1 adalah sisi panjang
    long_is_width = spec.width_cm >= spec.height_cm
    if long_is_a == long_is_width:
        return pts
    return np.array([pts[0], pts[3], pts[2], pts[1]])


def _plausible_mat(image: np.ndarray, pts: np.ndarray,
                   mat_color: tuple[int, int, int] | None = None) -> bool:
    """Permukaan alas harus relatif seragam; bila `mat_color` diberi,
    cincin dalam quad juga wajib berwarna mendekati warna alas standar.

    Keseragaman diukur pada kroma (a,b) LAB, bukan lightness: gradien
    cahaya/bayangan menggeser L tapi hampir tidak menggeser kroma,
    sehingga mat asli dengan pencahayaan tidak merata tetap lolos,
    sedangkan karpet bermotif (variasi kroma tinggi) tetap ditolak.
    Tubuh di tengah tidak memengaruhi cincin ini. Batas tanpa mat_color
    didokumentasikan di DEC-015.
    """
    mask = np.zeros(image.shape[:2], np.uint8)
    cv2.fillPoly(mask, [pts.astype(np.int32)], 255)
    eroded = cv2.erode(mask, np.ones((15, 15), np.uint8))
    ring = mask & ~eroded
    ring_px = ring > 0
    if int(ring_px.sum()) < 1000:
        return False
    gray_std = float(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[ring_px].std())
    if gray_std > MAX_RING_STD:
        return False
    if mat_color is not None:
        lab_img = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
        target = cv2.cvtColor(np.uint8([[mat_color]]), cv2.COLOR_BGR2LAB)[0, 0, 1:]
        chroma = lab_img[ring_px][:, 1:]
        dist = np.linalg.norm(chroma - target.astype(np.float32), axis=1)
        if float(np.median(dist)) > MAX_RING_CHROMA_DIST:
            return False
    return True
