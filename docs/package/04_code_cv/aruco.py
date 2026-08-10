"""Deteksi marker ArUco dan rektifikasi perspektif bidang alas (V1, V2, CV-01, CV-02).

Alas ukur memuat empat marker pada posisi yang diketahui. Dari keempatnya
dihitung homografi yang memetakan citra ke koordinat bidang alas dalam
sentimeter, sehingga jarak pada bidang tersebut dapat diukur langsung.

Batas yang harus dipegang (DEC-004): homografi hanya benar untuk titik yang
BERADA PADA bidang alas. Titik yang berada di atasnya -- misalnya tepi siluet
kepala -- tetap mengalami galat skala akibat parallax. Modul ini tidak
mengoreksinya; yang dilakukan adalah mengukur dan membatasi lewat quality
control (lihat `cv/geometry.py` dan CV-00).

Konvensi tata letak alas:

    marker ID 0 = kiri-atas       ID 1 = kanan-atas
    marker ID 3 = kiri-bawah      ID 2 = kanan-bawah

Titik acuan setiap marker adalah SUDUT LUARNYA (sudut yang menghadap ke luar
alas), sehingga jarak antar acuan sama dengan ukuran alas yang diukur meteran.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

DEFAULT_DICT = cv2.aruco.DICT_4X4_50
EXPECTED_IDS = (0, 1, 2, 3)

# Indeks sudut LUAR untuk tiap posisi marker. OpenCV mengembalikan sudut dalam
# urutan searah jarum jam mulai dari kiri-atas marker.
OUTER_CORNER = {0: 0, 1: 1, 2: 2, 3: 3}


@dataclass(frozen=True)
class MatSpec:
    """Ukuran fisik alas ukur, diukur antar sudut luar marker (sentimeter)."""

    width_cm: float
    height_cm: float
    marker_ids: tuple = EXPECTED_IDS
    dictionary: int = DEFAULT_DICT

    def object_points(self) -> np.ndarray:
        """Koordinat sudut luar tiap marker pada bidang alas, urut ID 0..3."""
        return np.array([
            [0.0, 0.0],                        # ID 0 kiri-atas
            [self.width_cm, 0.0],              # ID 1 kanan-atas
            [self.width_cm, self.height_cm],   # ID 2 kanan-bawah
            [0.0, self.height_cm],             # ID 3 kiri-bawah
        ], dtype=np.float64)


@dataclass
class DetectionResult:
    found_ids: list = field(default_factory=list)
    image_points: np.ndarray | None = None     # (4,2) piksel, urut ID 0..3
    homography: np.ndarray | None = None       # citra -> cm
    reprojection_error_px: float = float("nan")
    ok: bool = False
    reason: str = ""

    @property
    def missing_ids(self) -> list:
        return [i for i in EXPECTED_IDS if i not in self.found_ids]


def _detector(dictionary: int):
    d = cv2.aruco.getPredefinedDictionary(dictionary)
    params = cv2.aruco.DetectorParameters()
    # Refinement subpiksel penting: galat 1 px pada sudut marker langsung
    # menjadi galat milimeter pada hasil ukur.
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return cv2.aruco.ArucoDetector(d, params)


def detect_markers(image: np.ndarray, spec: MatSpec) -> DetectionResult:
    """Deteksi keempat marker dan hitung homografi bidang alas."""
    if image is None or image.size == 0:
        return DetectionResult(reason="citra kosong")

    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = _detector(spec.dictionary).detectMarkers(gray)

    if ids is None:
        return DetectionResult(reason="tidak ada marker terdeteksi")

    found = [int(i) for i in ids.flatten()]
    res = DetectionResult(found_ids=found)

    if not set(EXPECTED_IDS).issubset(found):
        res.reason = f"marker tidak lengkap; hilang {res.missing_ids}"
        return res

    pts = np.zeros((4, 2), dtype=np.float64)
    for marker_id in EXPECTED_IDS:
        k = found.index(marker_id)
        pts[marker_id] = corners[k][0][OUTER_CORNER[marker_id]]

    obj = spec.object_points()
    H, mask = cv2.findHomography(pts, obj, method=0)
    if H is None:
        res.reason = "homografi gagal dihitung"
        return res

    res.image_points = pts
    res.homography = H
    res.reprojection_error_px = _reprojection_error(H, pts, obj)
    res.ok = True
    return res


def _reprojection_error(H: np.ndarray, image_pts: np.ndarray, object_pts: np.ndarray) -> float:
    """RMS galat saat titik alas dipetakan balik ke citra.

    Nilai besar menandakan keempat titik tidak benar-benar sebidang: alas
    melengkung, marker terlipat, atau ada yang salah terdeteksi.
    """
    Hinv = np.linalg.inv(H)
    back = apply_homography(Hinv, object_pts)
    return float(np.sqrt(((back - image_pts) ** 2).sum(axis=1).mean()))


def apply_homography(H: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Terapkan homografi pada titik (n,2)."""
    p = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    homo = np.hstack([p, np.ones((len(p), 1))])
    out = (H @ homo.T).T
    w = out[:, 2:3]
    if np.any(np.abs(w) < 1e-12):
        raise ValueError("Titik berada pada garis di tak hingga; homografi tidak berlaku.")
    return out[:, :2] / w


def to_cm(det: DetectionResult, points_px: np.ndarray) -> np.ndarray:
    """Piksel -> sentimeter pada bidang alas."""
    if not det.ok:
        raise ValueError(f"Deteksi tidak valid: {det.reason}")
    return apply_homography(det.homography, points_px)


def distance_cm(det: DetectionResult, p1_px, p2_px) -> float:
    """Jarak dua titik PADA BIDANG ALAS, dalam sentimeter.

    Untuk titik yang tidak berada pada bidang alas, hasilnya bias -- besarnya
    diukur oleh CV-00, bukan diasumsikan kecil.
    """
    a, b = to_cm(det, np.array([p1_px, p2_px], dtype=np.float64))
    return float(np.hypot(*(b - a)))


def rectify(image: np.ndarray, det: DetectionResult, spec: MatSpec,
            px_per_cm: float = 10.0) -> np.ndarray:
    """Hasilkan citra tegak-lurus bidang alas, berskala tetap.

    Berguna untuk segmentasi (`cv/segment.py`) dan untuk ditampilkan ke kader
    sebagai umpan balik visual.
    """
    if not det.ok:
        raise ValueError(f"Deteksi tidak valid: {det.reason}")
    w = int(round(spec.width_cm * px_per_cm))
    h = int(round(spec.height_cm * px_per_cm))
    scale = np.array([[px_per_cm, 0, 0], [0, px_per_cm, 0], [0, 0, 1]], dtype=np.float64)
    return cv2.warpPerspective(image, scale @ det.homography, (w, h))


def draw_overlay(image: np.ndarray, det: DetectionResult) -> np.ndarray:
    """Tandai marker yang terdeteksi. Dipakai untuk umpan balik dan lampiran."""
    out = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if det.image_points is None:
        return out
    pts = det.image_points.astype(int)
    for i, (x, y) in enumerate(pts):
        cv2.circle(out, (x, y), 8, (0, 255, 0), -1)
        cv2.putText(out, str(i), (x + 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.polylines(out, [pts[[0, 1, 2, 3]].reshape(-1, 1, 2)], True, (0, 255, 0), 2)
    return out


def generate_marker_sheet(spec: MatSpec, marker_px: int = 400) -> dict:
    """Hasilkan keempat citra marker untuk dicetak.

    Cetak pada ukuran fisik yang sama, tempel di keempat sudut alas, lalu
    UKUR jarak antar sudut luarnya dengan meteran -- angka itulah yang masuk
    `MatSpec`, bukan ukuran nominal kertas.
    """
    d = cv2.aruco.getPredefinedDictionary(spec.dictionary)
    return {i: cv2.aruco.generateImageMarker(d, i, marker_px) for i in EXPECTED_IDS}


def save_marker_sheet(spec: MatSpec, out_dir: Path, marker_px: int = 400) -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in generate_marker_sheet(spec, marker_px).items():
        p = out_dir / f"aruco_{i}.png"
        cv2.imwrite(str(p), img)
        paths.append(p)
    return paths
