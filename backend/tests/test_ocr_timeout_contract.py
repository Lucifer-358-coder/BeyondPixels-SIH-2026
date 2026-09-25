"""Tesseract subprocesses have bounded per-call timeouts."""
from unittest.mock import patch
import pytesseract
from PIL import Image
from services import extract_text
from mrz_ocr import _ocr


def test_general_ocr_has_timeout():
    with patch.object(pytesseract, "image_to_string", return_value="FICTIONAL") as call:
        assert extract_text(Image.new("RGB", (100, 80)))["status"] == "completed"
    assert call.call_args.kwargs["timeout"] == 15


def test_mrz_ocr_has_timeout():
    with patch.object(pytesseract, "image_to_string", return_value="P<FICTIONAL") as call:
        _ocr(Image.new("RGB", (100, 80)), 7, 1)
    assert call.call_args.kwargs["timeout"] == 8
