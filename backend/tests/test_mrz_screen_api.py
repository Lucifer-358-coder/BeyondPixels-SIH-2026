"""End-to-end endpoint checks with fictional synthetic passport specimens."""
from __future__ import annotations

import io
import pytest
flask = pytest.importorskip("flask")
pytest.importorskip("flask_cors")
from app import app
from test_mrz_ocr import _specimen


@pytest.mark.parametrize("invalid,expected", [(False, "checks_passed"), (True, "checksum_mismatch")])
def test_screen_api_uses_dedicated_mrz_ocr(monkeypatch, invalid, expected):
    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "local-test-token")
    # This unit test is about MRZ, not the independent image-generation model.
    monkeypatch.setattr("app.detect_image", lambda *args, **kwargs: {
        "status": "completed", "ai_generated": None, "decision": "inconclusive"
    })
    specimen = _specimen(invalid)
    output = io.BytesIO()
    specimen.save(output, format="PNG")
    result = app.test_client().post(
        "/v1/screen", headers={"Authorization": "Bearer local-test-token"},
        data={"image": (io.BytesIO(output.getvalue()), "synthetic.png")},
    )
    assert result.status_code == 200, result.json
    assert result.json["ocr"]["status"] == "completed"
    assert result.json["ocr"]["mrz_extraction_status"] == "detected"
    assert result.json["ocr"]["raw_text_returned"] is False
    assert result.json["document_validation"]["status"] == expected
    assert result.json["screening_status"] == ("manual_review" if invalid else "inconclusive")
