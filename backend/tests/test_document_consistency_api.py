"""Flask route uses actual field comparisons, without invoking media classifiers."""
from __future__ import annotations

import io

import pytest
pytest.importorskip("flask")
pytest.importorskip("flask_cors")
from PIL import Image
import app as screening


def _call(monkeypatch, printed_expiry, mrz_expiry, checksum_ok=True):
    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "fixture-only-token")
    monkeypatch.setattr(screening, "detect_image", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("Document invoked AI-image model")))
    monkeypatch.setattr(screening, "analyze_deepfake", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("Document invoked deepfake model")))
    monkeypatch.setattr(screening, "extract_text", lambda _: {
        "status": "completed", "text": "FICTIONAL"})
    monkeypatch.setattr(screening, "extract_td3_mrz", lambda _: {
        "status": "detected", "text": "FICTIONAL-MRZ"})
    monkeypatch.setattr(screening, "inspect_passport_mrz", lambda _: {
        "status": "checks_passed" if checksum_ok else "checksum_mismatch",
        "document_type": "passport", "checks": {"expiry_date": checksum_ok}})
    monkeypatch.setattr(screening, "extract_labelled_fields", lambda _: {
        "expiry_date": printed_expiry})
    monkeypatch.setattr(screening, "integrate_expiry_ocr", lambda image, fields: (
        fields, {"status": "extracted", "method": "fixture"}))
    monkeypatch.setattr(screening, "extract_mrz_display_fields", lambda *a: {
        "expiry_date": mrz_expiry})
    b = io.BytesIO()
    Image.new("RGB", (80, 64), (255, 255, 255)).save(b, format="PNG")
    response = screening.app.test_client().post(
        "/v1/screen", headers={"Authorization": "Bearer fixture-only-token"},
        data={"image": (io.BytesIO(b.getvalue()), "fictional.png")},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_document_field_mismatch_shows_review_without_media(monkeypatch):
    result = _call(monkeypatch, "2031-08-21", "2030-01-01")
    assert result["screening_status"] == "manual_review"
    assert result["document_consistency"]["comparisons"]["expiry_date"] == "mismatch"
    assert result["tampering_localization"]["status"] == "not_assessed"
    assert result["image_generation"]["status"] == "not_applicable"
    assert result["deepfake"]["status"] == "not_implemented"
    assert "FICTIONAL-MRZ" not in str(result)


def test_document_agreement_does_not_claim_authenticity(monkeypatch):
    result = _call(monkeypatch, "2030-01-01", "2030-01-01")
    assert result["screening_status"] == "inconclusive"
    assert result["document_consistency"]["status"] == "no_comparable_discrepancy"
    assert "authenticity" in result["document_consistency"]["message"]


def test_bad_mrz_checksum_not_double_counted_as_field_mismatch(monkeypatch):
    result = _call(monkeypatch, "2031-08-21", "2030-01-01", checksum_ok=False)
    assert result["screening_status"] == "manual_review"
    assert result["document_consistency"]["mrz_checksum_issue"] is True
    assert result["document_consistency"]["comparisons"]["expiry_date"] == "not_compared"


def test_capabilities_distinguish_field_checks_from_visual_detector():
    response = screening.app.test_client().get("/v1/capabilities")
    assert response.status_code == 200
    modules = response.get_json()["modules"]
    assert modules["document_field_consistency"]["available"] is True
    assert modules["tampering_localization"]["available"] is True
    assert modules["tampering_localization"]["standalone_forgery_detection"] is False
