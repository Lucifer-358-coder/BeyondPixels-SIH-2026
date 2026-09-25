"""Document portrait stays isolated from AI/deepfake and returns no identity verdict."""
import io
from unittest.mock import patch

from PIL import Image
from app import app


def _png():
    output = io.BytesIO()
    Image.new("RGB", (256, 256), "white").save(output, format="PNG")
    return output.getvalue()


def test_document_portrait_contract(monkeypatch):
    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "portrait-unit-token")
    with patch("app.review_document_portrait", return_value={
        "status": "not_assessed", "finding": "no_frontal_face_candidate",
        "faces_detected": 0, "identity_verified": False,
        "portrait_replacement_detected": None,
    }) as mocked, patch("app.extract_text", return_value={"status": "unavailable", "text": ""}), \
         patch("app.analyze_deepfake", side_effect=AssertionError("must not run")), \
         patch("app.detect_image", side_effect=AssertionError("must not run")):
        response = app.test_client().post("/v1/screen",
            headers={"Authorization": "Bearer portrait-unit-token"},
            data={"image": (io.BytesIO(_png()), "synthetic.png")},
            content_type="multipart/form-data")
    assert response.status_code == 200
    body = response.get_json()
    mocked.assert_called_once()
    assert body["document_portrait_review"]["status"] == "not_assessed"
    assert body["deepfake"]["status"] == "not_implemented"
    assert body["image_generation"]["status"] == "not_applicable"
    assert body["face_verification"]["status"] == "not_assessed"
    assert body["face_verification"]["identity_verified"] is False
