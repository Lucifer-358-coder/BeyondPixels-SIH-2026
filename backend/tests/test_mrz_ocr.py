"""Image-level regression checks using newly generated fictional specimens."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from mrz import check_digit, inspect_passport_mrz
from mrz_ocr import extract_td3_mrz


def _specimen(invalid: bool = False):
    """Immutable recreated fixtures; do not assume these are user's original PNGs."""
    filename = "synthetic_recreated_invalid.png" if invalid else "synthetic_recreated_valid.png"
    with Image.open(Path(__file__).parent / "fixtures" / filename) as image:
        return image.convert("RGB")


@pytest.mark.parametrize("invalid,expected", [(False, "checks_passed"), (True, "checksum_mismatch")])
def test_recreated_specimen_mrz_is_read_and_validated(invalid, expected):
    result = extract_td3_mrz(_specimen(invalid))
    assert result["status"] == "detected", result
    assert [len(line) for line in result["text"].splitlines()] == [44, 44]
    checks = inspect_passport_mrz(result["text"])
    assert checks["status"] == expected, checks
    assert checks["checks"]["document_number"] is (not invalid)
    assert checks["checks"]["composite"] is (not invalid)


def test_blank_image_does_not_generate_mrz():
    assert extract_td3_mrz(Image.new("RGB", (1900, 550), "white")) == {
        "status": "not_detected", "text": ""
    }


def test_regular_text_document_does_not_generate_mrz():
    image = Image.new("RGB", (1400, 850), "white")
    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 37)
    draw = ImageDraw.Draw(image)
    for index, text in enumerate(("SYNTHETIC OCR TEST DOCUMENT", "Name: ALEX SAMPLE",
                                 "Document Number: TEST123456", "Status: SAMPLE ONLY")):
        draw.text((60, 100 + index * 100), text, font=font, fill="black")
    assert extract_td3_mrz(image)["status"] == "not_detected"
