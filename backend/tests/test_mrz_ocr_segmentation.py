"""Regression tests for photographed glyph segmentation, no checksum repair."""
from pathlib import Path

from PIL import Image
from mrz import inspect_passport_mrz
from mrz_ocr import extract_td3_mrz

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_synthetic_image_passes_all_five_checks():
    with Image.open(FIXTURES / "synthetic_recreated_valid.png") as image:
        result = extract_td3_mrz(image)
    assert result["status"] == "detected"
    assert [len(line) for line in result["text"].splitlines()] == [44, 44]
    assert result["text"].splitlines()[1].startswith("TST123456")
    inspected = inspect_passport_mrz(result["text"])
    assert inspected["status"] == "checks_passed"
    assert all(inspected["checks"].values())


def test_invalid_image_preserves_the_deliberate_change_and_fails_only_expected_checks():
    with Image.open(FIXTURES / "synthetic_recreated_invalid.png") as image:
        result = extract_td3_mrz(image)
    assert result["status"] == "detected"
    assert [len(line) for line in result["text"].splitlines()] == [44, 44]
    assert result["text"].splitlines()[1].startswith("XST123456")
    inspected = inspect_passport_mrz(result["text"])
    assert inspected["status"] == "checksum_mismatch"
    assert inspected["checks"] == {
        "document_number": False,
        "birth_date": True,
        "expiry_date": True,
        "optional_data": True,
        "composite": False,
    }


def test_blank_image_remains_not_detected():
    assert extract_td3_mrz(Image.new("RGB", (1900, 550), "white")) == {
        "status": "not_detected", "text": ""
    }
