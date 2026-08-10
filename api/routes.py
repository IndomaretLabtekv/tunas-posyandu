"""Endpoint: /measure, /manual-entry, /children, /priority."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Annotated, Any

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api import store
from api.schemas import MeasurementResponse
from cv.estimate import measure_or_estimate
from cv.mat_corners import PRODUCT_MAT_COLOR
from cv.pipeline import LOW_CONFIDENCE
from cv.quality import ImageQC
from cv.segment import ColorSegmenter
from tabular.who_lms import haz

router = APIRouter()

# Batas ukuran unggahan (bytes). Diubah menjadi test yang dapat diimpor.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# Rentang usia MVP: protokol recumbent 0-23 bulan penuh.
MIN_AGE_DAYS = 0
MAX_AGE_DAYS = 730


def _validate_demographics(sex: str, age_days: int) -> None:
    if sex.upper() not in {"M", "F"}:
        raise HTTPException(status_code=422, detail="sex harus M atau F")
    if not (MIN_AGE_DAYS <= age_days <= MAX_AGE_DAYS):
        raise HTTPException(
            status_code=422,
            detail=f"age_days harus antara {MIN_AGE_DAYS} dan {MAX_AGE_DAYS}",
        )


def _read_upload_limited(image: UploadFile, max_bytes: int) -> bytes:
    """Read upload in chunks; reject early if it exceeds max_bytes."""
    chunks: list[bytes] = []
    total = 0
    while chunk := image.file.read(8192):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"upload melebihi batas {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _decode_bgr(contents: bytes) -> np.ndarray | None:
    """Decode upload bytes to OpenCV BGR image."""
    buf = np.frombuffer(contents, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        return None
    return img


def _process_image(
    contents: bytes,
    sex: str,
    age_days: int,
) -> dict[str, Any]:
    """Run CV pipeline and return a plain result dict."""
    img = _decode_bgr(contents)
    if img is None:
        return {
            "mode": "rejected",
            "length_cm": None,
            "confidence": 0.0,
            "qc_reasons": ["gagal membaca citra"],
        }

    # EXIF focal fallback requires a real file path; keep it briefly.
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = Path(tmp.name)

        result = measure_or_estimate(
            img,
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
        m = result.measurement
        return {
            "mode": "measurement",
            "length_cm": m.length_cm,
            "confidence": m.confidence,
            "qc_reasons": m.qc_reasons or [],
            "haz": m.haz,
        }

    if result.mode == "estimate" and result.estimate is not None:
        e = result.estimate
        return {
            "mode": "estimate",
            "length_cm": e.length_cm,
            "confidence": e.confidence,
            "qc_reasons": e.reasons or [],
            "haz": None,
        }

    # Rejected: combine measurement and estimate failure reasons.
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


@router.post("/measurements", response_model=MeasurementResponse)
async def create_measurement(
    image: Annotated[UploadFile, File()],
    sex: Annotated[str, Form()],
    age_days: Annotated[int, Form()],
    name: Annotated[str, Form()] = "",
) -> MeasurementResponse:
    """Terima foto balita, jalankan pipeline CV, simpan, dan kembalikan hasil.

    Batas ukuran unggahan: MAX_UPLOAD_BYTES bytes (default 10 MiB).
    """
    _validate_demographics(sex, age_days)
    contents = _read_upload_limited(image, MAX_UPLOAD_BYTES)
    cv_result = _process_image(contents, sex, age_days)

    conn = store.get_conn()
    try:
        store.init_db(conn)
        child_id = store.create_child(conn, name=name, sex=sex)
        visit_id = store.record_visit(
            conn,
            child_id=child_id,
            age_days=age_days,
            mode=cv_result["mode"],
            length_cm=cv_result["length_cm"],
            confidence=cv_result["confidence"],
            haz=cv_result.get("haz"),
            qc_reasons=cv_result["qc_reasons"],
            low_confidence=cv_result["confidence"] < LOW_CONFIDENCE,
        )
    finally:
        conn.close()

    return MeasurementResponse(
        mode=cv_result["mode"],
        length_cm=cv_result["length_cm"],
        confidence=cv_result["confidence"],
        low_confidence=cv_result["confidence"] < LOW_CONFIDENCE,
        qc_reasons=cv_result["qc_reasons"],
        haz=cv_result.get("haz"),
        child_id=child_id,
        visit_id=visit_id,
    )
