"""Test FastAPI /measurements endpoint with real CV processing."""

import io

import cv2
import numpy as np
import pytest
from _cv_synth import synth_plain_mat_with_body
from fastapi.testclient import TestClient

from api.routes import MAX_UPLOAD_BYTES


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Build a TestClient with a temporary database."""
    db_path = tmp_path / "api_test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
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


def test_invalid_sex_returns_422_before_cv(client):
    img, _, _, _ = synth_plain_mat_with_body()
    response = client.post(
        "/measurements",
        data={"name": "Budi", "sex": "X", "age_days": "180"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    assert response.status_code == 422


def test_out_of_range_age_returns_422_before_cv(client):
    img, _, _, _ = synth_plain_mat_with_body()
    response = client.post(
        "/measurements",
        data={"name": "Budi", "sex": "M", "age_days": "731"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )
    assert response.status_code == 422


def test_oversized_upload_returns_413(client):
    huge = b"\x00" * (MAX_UPLOAD_BYTES + 1)
    response = client.post(
        "/measurements",
        data={"name": "Budi", "sex": "M", "age_days": "180"},
        files={"image": ("body.jpg", io.BytesIO(huge), "image/jpeg")},
    )
    assert response.status_code == 413


def test_per_test_database_isolation(client, tmp_path, monkeypatch):
    img, _, _, _ = synth_plain_mat_with_body()
    assert client.post(
        "/measurements",
        data={"name": "Budi", "sex": "M", "age_days": "180"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    ).status_code == 200

    other_db = tmp_path / "other.db"
    monkeypatch.setenv("DB_PATH", str(other_db))
    from api.main import app
    other_client = TestClient(app)
    other_client.post(
        "/measurements",
        data={"name": "Ani", "sex": "F", "age_days": "240"},
        files={"image": ("body.jpg", io.BytesIO(_encode_jpeg(img)), "image/jpeg")},
    )

    from api import store
    conn1 = store.get_conn(str(tmp_path / "api_test.db"))
    conn2 = store.get_conn(str(other_db))
    try:
        assert len(store.list_visits(conn1)) == 1
        assert len(store.list_visits(conn2)) == 1
    finally:
        conn1.close()
        conn2.close()
