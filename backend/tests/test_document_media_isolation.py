"""Document route does not run either media model; retain honest legacy keys."""
from __future__ import annotations

import io

import cv2
import numpy as np
import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_cors")
import app as application


def _png():
    encoded, buffer = cv2.imencode(".png", np.full((96, 96, 3), 255, dtype=np.uint8))
    assert encoded
    return buffer.tobytes()


def _client(monkeypatch, mrz_status="not_detected"):
    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "fictional-fixture-token")
    monkeypatch.setattr(application, "detect_image", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("Document route invoked whole-image classifier")))
    monkeypatch.setattr(application, "analyze_deepfake", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("Document route invoked face-manipulation classifier")))
    monkeypatch.setattr(application, "extract_text", lambda _: {"status": "unavailable", "text": ""})
    monkeypatch.setattr(application, "inspect_passport_mrz", lambda _: {
        "status": mrz_status, "document_type": "passport", "checks": {}})
    # OCR-unavailable path intentionally bypasses MRZ; tests below exercise that
    # and the manual-review case by patching OCR and MRZ explicitly.
    return application.app.test_client()


def _post(client):
    return client.post("/v1/screen", headers={"Authorization": "Bearer fictional-fixture-token"},
                       data={"image": (io.BytesIO(_png()), "fictional.png")})


def test_document_does_not_run_image_or_deepfake(monkeypatch):
    client = _client(monkeypatch)
    response = _post(client)
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["screening_status"] == "inconclusive"
    assert body["image_generation"]["status"] == "not_applicable"
    assert body["image_generation"]["ai_generated"] is None
    assert body["image_authenticity"]["status"] == "not_applicable"
    assert body["deepfake"]["status"] == "not_implemented"
    assert all("classifier flagged" not in note for note in body["review_notes"])


def test_document_mrz_problem_still_requires_review(monkeypatch):
    client = _client(monkeypatch, mrz_status="checksum_mismatch")
    monkeypatch.setattr(application, "extract_text", lambda _: {"status": "completed", "text": "FICTIONAL"})
    monkeypatch.setattr(application, "extract_td3_mrz", lambda _: {
        "status": "detected", "text": "FICTIONAL"})
    monkeypatch.setattr(application, "integrate_expiry_ocr", lambda image, fields: (
        fields, {"status": "not_found", "method": "test"}))
    response = _post(client)
    assert response.status_code == 200, response.get_json()
    assert response.get_json()["screening_status"] == "manual_review"
    assert response.get_json()["image_generation"]["status"] == "not_applicable"


def test_document_requires_correct_token(monkeypatch):
    client = _client(monkeypatch)
    response = client.post("/v1/screen", headers={"Authorization": "Bearer wrong"},
                           data={"image": (io.BytesIO(_png()), "fictional.png")})
    assert response.status_code == 401
