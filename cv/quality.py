"""Quality control citra (V3, CV-03): blur, keterbacaan marker, framing.

Menggabungkan cek non-geometri di sini dengan GeometryQC (kemiringan kamera)
dari `cv.geometry`. Penolakan lebih baik daripada memberi angka yang salah:
sistem punya fallback input manual (SCOPE P3).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from cv.aruco import DetectionResult, MatSpec
from cv.geometry import GeometryQC


def blur_variance(gray: np.ndarray) -> float:
    """Varians Laplacian; makin kecil makin buram. Ambangnya empiris (CV-03)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


@dataclass
class ImageQC:
    """Cek non-geometri + delegasi geometry QC.

    Ambang default bersifat operasional dan wajib dikalibrasi dari CV-03/CV-04
    (kurva ambang vs galat hilir) sebelum angka dipakai di paper.
    """

    min_blur_var: float = 100.0
    min_marker_margin_frac: float = 0.02  # marker harus di dalam 2% tepi bingkai
    geometry: GeometryQC = field(default_factory=GeometryQC)

    def check(self, image: np.ndarray, det: DetectionResult, spec: MatSpec,
              camera_height_cm: float | None = None) -> dict:
        """Terima/tolak citra; `det` harus hasil `cv.aruco.detect_markers`."""
        gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = blur_variance(gray)
        reasons = []

        if blur < self.min_blur_var:
            reasons.append(f"citra buram (laplacian var {blur:.0f} < {self.min_blur_var})")

        if not det.ok:
            reasons.append(det.reason)
        else:
            h, w = image.shape[:2]
            m = self.min_marker_margin_frac
            pts = det.image_points
            x_min, x_max = float(pts[:, 0].min()), float(pts[:, 0].max())
            y_min, y_max = float(pts[:, 1].min()), float(pts[:, 1].max())
            if x_min < m * w or x_max > (1 - m) * w or y_min < m * h or y_max > (1 - m) * h:
                reasons.append("alas/penanda terpotong bingkai")

        geo = self.geometry.check(det, spec, camera_height_cm)
        reasons += geo["reasons"]

        return {
            "passed": not reasons,
            "reasons": reasons,
            "blur_var": round(blur, 1),
            "geometry": geo,
        }
