"""Orkestrasi kanal visual: citra -> panjang badan (cm) + confidence (V6).

Alur (DEC-004/005/011/015):
1. Deteksi referensi skala + homografi bidang alas  (V1, V2)
   -- default: 4 sudut alas polos (markerless, `cv/mat_corners.py`);
   -- mode marker ArUco tetap tersedia via argumen `detector`.
2. QC citra: blur, framing, kemiringan kamera       (V3)  -- gagal = TOLAK
3. Rektifikasi (tampak tegak lurus)                 (V2)
4. Segmentasi subjek vs alas                        (V4)  -- backend configurable
5. Endpoint kepala/tumit dari siluet                (V4)
6. Panjang di bidang alas (cm)                      (V6)
7. QC postur: siluet wajib + pose opsional          (V5a/V5b) -- menurunkan
   confidence, TIDAK menolak
8. HAZ opsional bila sex + age_days + haz_fn diberi (V6)

Semua ambang di sini operasional; kalibrasi dari CV-00/CV-03/CV-06.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from cv.aruco import MatSpec, apply_homography, rectify
from cv.geometry import measure_length_cm
from cv.mat_corners import detect_mat_corners
from cv.posture import SilhouettePostureQC, ViTPosePostureQC
from cv.quality import ImageQC
from cv.segment import BaseSegmenter, endpoints_from_mask, get_segmenter

# Ambang operasional -- lihat header modul.
LOW_CONFIDENCE = 0.4
POSTURE_PENALTY_PER_REASON = 0.25
POSTURE_PENALTY_CAP = 0.6


@dataclass
class MeasurementResult:
    ok: bool
    length_cm: float | None = None
    endpoints_px: tuple | None = None
    model: str = ""
    confidence: float = 0.0
    flagged_low: bool = False
    qc_reasons: list = field(default_factory=list)
    latency_s: float = 0.0
    haz: float | None = None
    reprojection_px: float = float("nan")


def measure_length(
    image: np.ndarray,
    mat_spec: MatSpec,
    segmenter: BaseSegmenter | None = None,
    image_qc: ImageQC | None = None,
    posture_qc: SilhouettePostureQC | None = None,
    vitpose_qc: ViTPosePostureQC | None = None,
    camera_height_cm: float | None = None,
    sex: str | None = None,
    age_days: int | None = None,
    haz_fn=None,
    px_per_cm: float = 10.0,
    detector=detect_mat_corners,
) -> MeasurementResult:
    """Ukur panjang badan dari satu citra. Gagal = ok=False (fallback manual).

    `detector` adalah callable (image, mat_spec) -> DetectionResult;
    default `cv.mat_corners.detect_mat_corners` (alas polos, DEC-015).
    Mode marker ArUco: lewatkan `detector=cv.aruco.detect_markers`.
    """
    t0 = time.perf_counter()
    segmenter = segmenter or get_segmenter("birefnet")
    image_qc = image_qc or ImageQC()
    posture_qc = posture_qc or SilhouettePostureQC()
    reasons: list[str] = []

    det = detector(image, mat_spec)
    if not det.ok:
        return MeasurementResult(ok=False, model=segmenter.model_name,
                                 qc_reasons=[det.reason], latency_s=time.perf_counter() - t0)

    qc = image_qc.check(image, det, mat_spec, camera_height_cm)
    if not qc["passed"]:
        return MeasurementResult(ok=False, model=segmenter.model_name,
                                 qc_reasons=qc["reasons"],
                                 reprojection_px=qc["geometry"]["reprojection_px"],
                                 latency_s=time.perf_counter() - t0)

    rect = rectify(image, det, mat_spec, px_per_cm=px_per_cm)
    seg = segmenter.segment(rect)
    if not seg.ok:
        return MeasurementResult(ok=False, model=seg.model, qc_reasons=[seg.reason],
                                 latency_s=time.perf_counter() - t0)

    end_rect = endpoints_from_mask(seg.mask)
    if end_rect is None:
        return MeasurementResult(ok=False, model=seg.model,
                                 qc_reasons=["siluet terlalu kecil untuk endpoint"],
                                 latency_s=time.perf_counter() - t0)

    # Peta endpoint citra teregistrasi -> piksel citra asli, lalu ukur di
    # bidang alas. Sisa galat elevasi titik kepala diukur CV-00, bukan
    # dikoreksi di sini (DEC-004).
    full = np.array([[px_per_cm, 0, 0], [0, px_per_cm, 0], [0, 0, 1]]) @ det.homography
    orig_pts = apply_homography(np.linalg.inv(full),
                                np.asarray(end_rect, dtype=np.float64))
    length_cm = measure_length_cm(det, orig_pts[0], orig_pts[1])

    posture = posture_qc.check(seg.mask)
    reasons += posture["reasons"]

    confidence = 1.0
    penalty = min(POSTURE_PENALTY_CAP, POSTURE_PENALTY_PER_REASON * len(posture["reasons"]))
    confidence -= penalty

    if vitpose_qc is not None:
        vp = vitpose_qc.check(rect)          # opsional; None bila tidak tersedia
        if vp is not None and not vp["passed"]:
            reasons.append(f"pose QC lemah (mean conf {vp['mean_conf']})")
            confidence -= 0.2

    confidence = float(np.clip(confidence, 0.0, 1.0))

    haz = None
    if haz_fn is not None and sex is not None and age_days is not None:
        haz = haz_fn(length_cm, sex, age_days)

    return MeasurementResult(
        ok=True, length_cm=round(float(length_cm), 2),
        endpoints_px=tuple(tuple(int(round(v)) for v in p) for p in orig_pts),
        model=seg.model, confidence=round(confidence, 3),
        flagged_low=confidence < LOW_CONFIDENCE,
        qc_reasons=reasons, latency_s=round(time.perf_counter() - t0, 3),
        haz=haz, reprojection_px=det.reprojection_error_px,
    )
