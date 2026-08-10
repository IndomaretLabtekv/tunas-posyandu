"""Shared CV processing service for legacy and workflow endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, BinaryIO

import cv2
import numpy as np
from fastapi import HTTPException

from cv.estimate import measure_or_estimate
from cv.mat_corners import PRODUCT_MAT_COLOR
from cv.quality import ImageQC
from cv.segment import ColorSegmenter
from tabular.who_lms import haz

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def read_upload_limited(file: BinaryIO, max_bytes: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read an upload incrementally and reject it once the limit is exceeded."""
    chunks: list[bytes] = []
    total = 0
    while chunk := file.read(8192):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"upload melebihi batas {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_bgr(contents: bytes) -> np.ndarray | None:
    buf = np.frombuffer(contents, dtype=np.uint8)
    image = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        return None
    return image


def process_image(contents: bytes, sex: str, age_days: int) -> dict[str, Any]:
    """Run the existing CV path and return its storage-safe structured result."""
    image = _decode_bgr(contents)
    if image is None:
        return {
            "mode": "rejected",
            "length_cm": None,
            "confidence": 0.0,
            "qc_reasons": ["gagal membaca citra"],
            "haz": None,
        }

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        result = measure_or_estimate(
            image,
            image_path=tmp_path,
            segmenter=ColorSegmenter(mat_color=PRODUCT_MAT_COLOR),
            image_qc=ImageQC(min_blur_var=1.0),
            sex=sex,
            age_days=age_days,
            haz_fn=haz,
        )
    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    if result.mode == "measurement" and result.measurement is not None:
        measurement = result.measurement
        return {
            "mode": "measurement",
            "length_cm": measurement.length_cm,
            "confidence": measurement.confidence,
            "qc_reasons": measurement.qc_reasons or [],
            "haz": measurement.haz,
        }

    if result.mode == "estimate" and result.estimate is not None:
        estimate = result.estimate
        return {
            "mode": "estimate",
            "length_cm": estimate.length_cm,
            "confidence": estimate.confidence,
            "qc_reasons": estimate.reasons or [],
            "haz": None,
        }

    reasons: list[str] = []
    if result.measurement is not None:
        reasons.extend(result.measurement.qc_reasons or [])
    if result.estimate is not None:
        reasons.extend(result.estimate.reasons or [])
    return {
        "mode": "rejected",
        "length_cm": None,
        "confidence": 0.0,
        "qc_reasons": reasons or ["tidak dapat mengukur maupun mengestimasi"],
        "haz": None,
    }
