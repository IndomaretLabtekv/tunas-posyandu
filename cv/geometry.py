"""Analisis plane-offset dan geometry quality control (DEC-004, DEC-011).

Homografi bidang alas hanya benar untuk titik yang berada PADA bidang itu.
Untuk titik yang berada z sentimeter di atas alas, dengan kamera pada
ketinggian H, skalanya meleset kira-kira:

    faktor = H / (H - z)

Kamera 100 cm dengan z = 10 cm sudah menghasilkan galat ~11%; pada panjang
70 cm itu berarti beberapa sentimeter. Karena itu sistem TIDAK mengklaim
mengoreksi parallax, melainkan:

1.  Mengukur besarnya lewat CV-00 pada objek berelevasi diketahui.
2.  Membatasinya lewat protokol: tinggi kamera minimum, kamera mendekati
    tegak lurus, objek dekat pusat bingkai.
3.  Menolak citra yang melanggar batas itu (geometry QC).

Yang menentukan galat bukan ketebalan tubuh secara keseluruhan, melainkan
elevasi TITIK YANG DIUKUR. Tumit menyentuh alas (z kira-kira 0); tepi siluet
kepala berada di sekitar setengah tinggi kepala. Karena itu objek uji CV-00
harus menyertakan bentuk membulat pada elevasi diketahui, bukan hanya pelat
datar. Parallax juga paling kecil di pusat bingkai dan membesar ke tepi.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cv.aruco import DetectionResult, MatSpec, apply_homography

# Ambang default. HARUS diganti dengan angka hasil CV-00, bukan dipakai apa adanya.
DEFAULT_MAX_TILT_DEG = 12.0
DEFAULT_MAX_REPROJ_PX = 3.0
DEFAULT_MIN_CAMERA_HEIGHT_CM = 120.0


def scale_error_factor(camera_height_cm: float, object_elevation_cm: float) -> float:
    """Faktor pembesaran akibat objek berada di atas bidang alas."""
    if camera_height_cm <= 0:
        raise ValueError("Tinggi kamera harus > 0.")
    if object_elevation_cm < 0:
        raise ValueError("Elevasi objek tidak boleh negatif.")
    if object_elevation_cm >= camera_height_cm:
        raise ValueError("Elevasi objek tidak boleh >= tinggi kamera.")
    return camera_height_cm / (camera_height_cm - object_elevation_cm)


def expected_bias_cm(true_length_cm: float, camera_height_cm: float,
                     object_elevation_cm: float) -> float:
    """Perkiraan galat panjang (cm) menurut model pinhole sederhana.

    Ini pembanding teoretis untuk hasil CV-00, bukan koreksi. Kalau galat
    terukur jauh berbeda dari sini, penyebabnya bukan hanya parallax --
    kemungkinan kalibrasi alas, distorsi lensa, atau deteksi sudut marker.
    """
    return true_length_cm * (scale_error_factor(camera_height_cm, object_elevation_cm) - 1.0)


def min_camera_height_for_tolerance(object_elevation_cm: float, true_length_cm: float,
                                    tolerance_cm: float) -> float:
    """Tinggi kamera minimum agar galat parallax tetap di bawah toleransi.

    Dipakai untuk menetapkan protokol pengambilan citra dari hasil CV-00.
    """
    if tolerance_cm <= 0:
        raise ValueError("Toleransi harus > 0.")
    ratio = tolerance_cm / true_length_cm
    return object_elevation_cm * (1.0 + 1.0 / ratio)


def camera_tilt_deg(det: DetectionResult, spec: MatSpec) -> float:
    """Perkiraan kemiringan kamera terhadap normal bidang alas.

    Diturunkan dari seberapa jauh alas persegi panjang tampak sebagai
    trapesium. Ini PROKSI, bukan pose kamera sebenarnya: pose yang tepat
    membutuhkan parameter intrinsik dan koefisien distorsi kamera, yang tidak
    tersedia untuk HP kader yang beragam (DEC-004).
    """
    if not det.ok:
        raise ValueError(f"Deteksi tidak valid: {det.reason}")
    p = det.image_points
    top = np.linalg.norm(p[1] - p[0])
    bottom = np.linalg.norm(p[2] - p[3])
    left = np.linalg.norm(p[3] - p[0])
    right = np.linalg.norm(p[2] - p[1])

    ratios = []
    for a, b in ((top, bottom), (left, right)):
        lo, hi = sorted((a, b))
        if lo <= 1e-9:
            return 90.0
        ratios.append(hi / lo)
    # Konversi heuristik: rasio 1.0 -> 0 derajat; makin timpang makin miring.
    worst = max(ratios)
    return float(np.degrees(np.arctan(worst - 1.0)) * 2.0)


def off_center_fraction(det: DetectionResult, point_px, image_shape) -> float:
    """Seberapa jauh titik dari pusat bingkai, 0 (pusat) sampai 1 (tepi).

    Parallax membesar ke tepi bingkai, jadi posisi objek ikut menentukan galat.
    """
    h, w = image_shape[:2]
    cx, cy = w / 2.0, h / 2.0
    x, y = np.asarray(point_px, dtype=float).ravel()[:2]
    return float(np.hypot((x - cx) / cx, (y - cy) / cy) / np.sqrt(2))


@dataclass
class GeometryQC:
    max_tilt_deg: float = DEFAULT_MAX_TILT_DEG
    max_reprojection_px: float = DEFAULT_MAX_REPROJ_PX
    min_camera_height_cm: float | None = None

    def check(self, det: DetectionResult, spec: MatSpec,
              camera_height_cm: float | None = None) -> dict:
        """Terima atau tolak citra berdasarkan geometrinya.

        Menolak lebih baik daripada memberi angka yang salah: sistem punya
        fallback input manual, sehingga penolakan tidak menggagalkan alur.
        """
        if not det.ok:
            return {"passed": False, "reasons": [det.reason], "tilt_deg": float("nan"),
                    "reprojection_px": float("nan")}

        tilt = camera_tilt_deg(det, spec)
        reasons = []
        if tilt > self.max_tilt_deg:
            reasons.append(f"kamera terlalu miring ({tilt:.1f} deg > {self.max_tilt_deg})")
        # ponytail: reprojection 4-titik TIDAK dipakai sebagai penolakan. Homografi
        # dihitung dari tepat 4 titik lalu di-reproject titik yang sama, sehingga
        # residual ~0 by construction dan tidak pernah memicu. Nilai tetap
        # dilaporkan sebagai diagnostik; residual yang bermakna membutuhkan
        # geometri 16 sudut marker (MatSpec diperluas) -- Future Work.
        if self.min_camera_height_cm is not None:
            if camera_height_cm is None:
                reasons.append("tinggi kamera tidak diketahui")
            elif camera_height_cm < self.min_camera_height_cm:
                reasons.append(
                    f"kamera terlalu dekat ({camera_height_cm:.0f} < {self.min_camera_height_cm:.0f} cm)"
                )

        return {
            "passed": not reasons,
            "reasons": reasons,
            "tilt_deg": round(tilt, 2),
            "reprojection_px": round(det.reprojection_error_px, 3),
        }


def measure_length_cm(det: DetectionResult, head_px, heel_px) -> float:
    """Panjang badan dari dua titik ujung, tanpa koreksi elevasi.

    Nama fungsi sengaja tidak mengandung kata "koreksi": nilai yang dihasilkan
    adalah panjang pada bidang alas. Galat sisa akibat elevasi titik kepala
    dilaporkan terpisah lewat CV-00, bukan disembunyikan di dalam sini.
    """
    a, b = apply_homography(det.homography, np.array([head_px, heel_px], dtype=float))
    return float(np.hypot(*(b - a)))
