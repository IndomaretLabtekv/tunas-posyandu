"""Test FastAPI /measurements endpoint with real CV processing."""

import io
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import sys

# Ensure tests/ helpers are importable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cv_synth import STANDARD_MAT_COLOR, synth_plain_mat_with_body  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a TestClient with a temporary database."""
    db_path = tmp_path / "api_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # DB_PATH is read at import time in api.main, so import here after env is set.
    from api.main import app
    return TestClient(app)


def _encode_jpeg(bgr_image: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".jpg", bgr_image)
    assert ok
    return buf.tobytes()


def test_post_measurement_with_mat_returns_measurement_mode(client):
    img, _, _, _ = synth_plain_mat_with_body()
    response = client.post(
        "/measurements",
        data={"name": "Budi", "sex": "M", "age_days": "180"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "measurement"
    assert payload["length_cm"] is not None
    assert payload["length_cm"] > 0
    assert payload["confidence"] > 0
    assert payload["low_confidence"] is False
    assert payload["qc_reasons"] == []
    assert payload["haz"] is not None
    assert payload["child_id"] is not None
    assert payload["visit_id"] is not None


def test_post_measurement_without_mat_returns_estimate_mode(client):
    # Blanket-only scene forces the pipeline into estimate mode (DEC-016).
    img = np.full((400, 500, 3), (200, 120, 60), np.uint8)
    cv2.circle(img, (200, 200), 40, (140, 170, 220), -1)
    cv2.ellipse(img, (320, 220), (90, 30), 0, 0, 360, (140, 170, 220), -1)
    response = client.post(
        "/measurements",
        data={"name": "Ani", "sex": "F", "age_days": "240"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["mode"] == "estimate"
    assert payload["length_cm"] is not None
    assert payload["confidence"] == pytest.approx(0.3)
    assert payload["low_confidence"] is True
    assert payload["qc_reasons"]
    assert payload["child_id"] is not None
    assert payload["visit_id"] is not None


def test_post_measurement_rejects_unparseable_image(client):
    response = client.post(
        "/measurements",
        data={"name": "Budi", "sex": "M", "age_days": "180"},
        files={"image": ("body.jpg", io.BytesIO(b"not an image"), "image/jpeg")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "rejected"
    assert payload["length_cm"] is None
    assert payload["haz"] is None
    assert payload["low_confidence"] is True
    assert payload["qc_reasons"]


def test_post_measurement_requires_sex_and_age(client):
    img, _, _, _ = synth_plain_mat_with_body()
    response = client.post(
        "/measurements",
        data={"name": "Budi"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    assert response.status_code == 422


def test_response_includes_mode_confidence_qc_and_low_confidence(client):
    img, _, _, _ = synth_plain_mat_with_body()
    response = client.post(
        "/measurements",
        data={"name": "Citra", "sex": "F", "age_days": "365"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    payload = response.json()
    assert "mode" in payload
    assert "confidence" in payload
    assert "qc_reasons" in payload
    assert "low_confidence" in payload
