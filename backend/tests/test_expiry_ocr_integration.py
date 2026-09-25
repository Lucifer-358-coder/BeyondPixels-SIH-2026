"""Focused checks for the OCR adapter and /v1/screen wiring.

The live-image smoke tests reuse previously evaluated fictional images;
they are integration checks, NOT new independent OCR evaluation.
"""
from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path

import pytest
from PIL import Image

import expiry_ocr_bridge as bridge


def _stub(monkeypatch, response):
    monkeypatch.setattr(bridge, "_run_locked_extractor", lambda image: response)


def test_label_above_value_adds_expiry(monkeypatch):
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2034-08-21", "method": "spatial_v01"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"name": "FICTIONAL"})
    assert fields == {"name": "FICTIONAL", "expiry_date": "2034-08-21"}
    assert report == {"status": "extracted", "method": "spatial_v01"}


def test_negative_does_not_guess_birth_date(monkeypatch):
    _stub(monkeypatch, {"status": "not_found", "expiry_date": None, "method": "label_anchored_crop_v03"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"date_of_birth": "2002-02-14"})
    assert "expiry_date" not in fields
    assert report["status"] == "not_found"


def test_matching_same_line_value_is_preserved(monkeypatch):
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2034-08-21", "method": "spatial_v01"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"expiry_date": "2034-08-21"})
    assert fields["expiry_date"] == "2034-08-21"
    assert report["status"] == "extracted"


def test_conflicting_same_line_date_is_not_silently_overwritten(monkeypatch):
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2034-08-21", "method": "spatial_v01"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"expiry_date": "2035-08-21"})
    assert "expiry_date" not in fields
    assert report["status"] == "conflict"


def test_ambiguous_result_suppresses_old_field(monkeypatch):
    _stub(monkeypatch, {"status": "ambiguous", "expiry_date": None, "method": "spatial_v01"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"expiry_date": "2034-08-21"})
    assert "expiry_date" not in fields
    assert report["status"] == "ambiguous"


def test_optional_extractor_unavailable_keeps_legacy_field(monkeypatch):
    def unavailable(image):
        raise RuntimeError("Do not expose local exception details")

    monkeypatch.setattr(bridge, "_run_locked_extractor", unavailable)
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {"expiry_date": "2034-08-21"})
    assert fields["expiry_date"] == "2034-08-21"
    assert report == {"status": "unavailable", "method": None}
    assert "exception" not in str(report).lower()


def test_invalid_extractor_date_is_not_displayed(monkeypatch):
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2044-99-99", "method": "spatial_v01"})
    fields, report = bridge.integrate_expiry_ocr(Image.new("RGB", (30, 30)), {})
    assert "expiry_date" not in fields
    assert report["status"] == "unavailable"


def _png_bytes():
    output = BytesIO()
    Image.new("RGB", (120, 70), "white").save(output, format="PNG")
    return output.getvalue()


def _app_with_mock_dependencies(monkeypatch):
    pytest.importorskip("flask")
    pytest.importorskip("flask_cors")
    import app as module

    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "local-test-token")
    monkeypatch.setattr(module, "extract_text", lambda image: {
        "status": "completed", "text": "NAME: FICTIONAL\nEXPIRY DATE\n2034-08-21"
    })
    monkeypatch.setattr(module, "extract_td3_mrz", lambda image: {"status": "not_detected", "text": ""})
    monkeypatch.setattr(module, "inspect_passport_mrz", lambda text: {
        "status": "not_detected", "document_type": "unknown", "checks": {}
    })
    monkeypatch.setattr(module, "detect_image", lambda *args, **kwargs: {
        "status": "unavailable", "ai_generated": None
    })
    module.app.config.update(TESTING=True)
    return module.app.test_client()


def test_screen_endpoint_exposes_expiry_and_preserves_mrz(monkeypatch):
    client = _app_with_mock_dependencies(monkeypatch)
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2034-08-21", "method": "spatial_v01"})
    response = client.post(
        "/v1/screen",
        data={"image": (BytesIO(_png_bytes()), "fictional.png")},
        headers={"Authorization": "Bearer local-test-token"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["ocr"]["fields"]["expiry_date"] == "2034-08-21"
    assert body["ocr"]["expiry_extraction"] == {"status": "extracted", "method": "spatial_v01"}
    assert body["ocr"]["raw_text_returned"] is False
    assert body["ocr"]["mrz_fields_verified"] is False
    assert body["document_validation"]["status"] == "not_detected"
    assert "text" not in body["ocr"]


def test_screen_endpoint_handles_no_expiry_without_ui_changes(monkeypatch):
    client = _app_with_mock_dependencies(monkeypatch)
    _stub(monkeypatch, {"status": "not_found", "expiry_date": None, "method": "label_anchored_crop_v03"})
    response = client.post(
        "/v1/screen",
        data={"image": (BytesIO(_png_bytes()), "fictional.png")},
        headers={"Authorization": "Bearer local-test-token"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert "expiry_date" not in body["ocr"]["fields"]
    assert body["ocr"]["expiry_extraction"]["status"] == "not_found"



def test_screen_endpoint_retains_mrz_validation(monkeypatch):
    client = _app_with_mock_dependencies(monkeypatch)
    import app as module
    monkeypatch.setattr(module, "extract_td3_mrz", lambda image: {
        "status": "detected", "text": "synthetic-test-mrz"
    })
    monkeypatch.setattr(module, "inspect_passport_mrz", lambda text: {
        "status": "valid", "document_type": "passport", "checks": {"expiry_date": True}
    })
    monkeypatch.setattr(module, "extract_mrz_display_fields", lambda text, mrz: {
        "expiry_date": "2034-08-21", "document_number_masked": "*****1234"
    })
    _stub(monkeypatch, {"status": "extracted", "expiry_date": "2034-08-21", "method": "spatial_v01"})
    response = client.post(
        "/v1/screen",
        data={"image": (BytesIO(_png_bytes()), "fictional.png")},
        headers={"Authorization": "Bearer local-test-token"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["document_validation"]["status"] == "valid"
    assert body["ocr"]["mrz_extraction_status"] == "detected"
    assert body["ocr"]["mrz_fields"] == {
        "expiry_date": "2034-08-21", "document_number_masked": "*****1234"
    }
    assert body["ocr"]["fields"]["expiry_date"] == "2034-08-21"


def test_screen_endpoint_skips_spatial_when_general_ocr_unavailable(monkeypatch):
    client = _app_with_mock_dependencies(monkeypatch)
    import app as module
    monkeypatch.setattr(module, "extract_text", lambda image: {
        "status": "unavailable", "text": ""
    })
    monkeypatch.setattr(bridge, "_run_locked_extractor", lambda image: (
        (_ for _ in ()).throw(AssertionError("spatial OCR should not run"))
    ))
    response = client.post(
        "/v1/screen",
        data={"image": (BytesIO(_png_bytes()), "fictional.png")},
        headers={"Authorization": "Bearer local-test-token"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["ocr"]["fields"] == {}
    assert body["ocr"]["expiry_extraction"]["status"] == "not_checked"


def test_real_saved_fictional_images_smoke():
    """Previously evaluated images: integration smoke, not a fresh benchmark."""
    import shutil
    if shutil.which("tesseract") is None:
        pytest.skip("Install Tesseract or add its directory to PATH")
    from media import open_document_image

    root = (Path(__file__).resolve().parents[1] /
            "data/research_single_image_documents_v01")
    inventory_path = root / "v03_new_evaluation_references/inventory.json"
    if not inventory_path.is_file():
        pytest.skip("Previously evaluated fictional images not available in this checkout")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    records = {item["family_id"]: item for item in inventory["references"]}

    for number in (21, 25):
        family = f"fictional_document_{number:02d}"
        record = records[family]
        reference = root / "v03_new_evaluation_references" / record["file"]
        image = open_document_image(reference.read_bytes())
        fields, report = bridge.integrate_expiry_ocr(image, {})
        assert report["status"] == "extracted", (family, report)
        assert fields["expiry_date"] == record["expected_reference_expiry"]

        negative = (root / "v03_new_evaluation_variants" / family /
                    "birth_date_only_no_expiry_label.png")
        image = open_document_image(negative.read_bytes())
        fields, report = bridge.integrate_expiry_ocr(image, {})
        assert report["status"] == "not_found", (family, report)
        assert "expiry_date" not in fields
