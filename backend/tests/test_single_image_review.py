"""Synthetic document evidence only; no real identities or authenticity claims."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
pytest.importorskip('pytesseract')
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from single_image_review import localize_disputed_printed_fields

ROOT = Path(__file__).resolve().parents[1]


def _image():
    # Installation test passes using the fixture packaged alongside installer
    # (installed tests are self-contained by mocking the exact OCR geometry).
    return Image.new('RGB', (1900, 940), 'white')


def _ocr_words():
    texts = ['EXPIRY', 'DATE:', '2031-08-21']
    return dict(text=texts, conf=['95', '96', '96'],
                left=[69, 223, 358], top=[310, 310, 310],
                width=[128, 100, 217], height=[27, 27, 27],
                page_num=[1]*3, block_num=[1]*3, par_num=[1]*3, line_num=[4]*3)


def _patch_ocr(monkeypatch, words=None, fail=False):
    import pytesseract
    if fail:
        def fake(*args, **kwargs):
            raise RuntimeError('OCR unavailable')
    else:
        def fake(*args, **kwargs):
            return words if words is not None else _ocr_words()
    monkeypatch.setattr(pytesseract, 'image_to_data', fake)


def test_correlated_expiry_mismatch_locates_single_image_printed_value(monkeypatch):
    _patch_ocr(monkeypatch)
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'expiry_date': 'mismatch'}}, {'expiry_date': '2031-08-21'})
    assert result['status'] == 'completed' and result['regions_detected'] == 1
    assert result['top_regions'][0]['field'] == 'expiry_date'
    assert .15 < result['top_regions'][0]['x'] < .25
    assert .30 < result['top_regions'][0]['y'] < .40
    assert '2031' not in json.dumps(result)
    assert 'forgery' in result['limitation']


def test_matching_fields_do_not_produce_artifact_or_authenticity_claim(monkeypatch):
    _patch_ocr(monkeypatch, fail=True)
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'expiry_date': 'match'}}, {'expiry_date': '2030-01-01'})
    assert result['status'] == 'not_assessed'
    assert result['top_regions'] == [] and result['overlay_available'] is False


def test_no_mismatch_and_no_ocr_makes_no_claim(monkeypatch):
    _patch_ocr(monkeypatch, fail=True)
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'expiry_date': 'mismatch'}}, {'expiry_date': '2031-08-21'})
    assert result['reason'] == 'geometry_ocr_unavailable'
    assert result['regions_detected'] == 0


def test_value_mismatch_does_not_localize_unrelated_same_line(monkeypatch):
    _patch_ocr(monkeypatch, {**_ocr_words(), 'text': ['EXPIRY','DATE:', '2030-01-01']})
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'expiry_date': 'mismatch'}}, {'expiry_date': '2031-08-21'})
    assert result['reason'] == 'mismatch_not_localized'


def test_unlabelled_date_and_mrz_date_are_not_boxes(monkeypatch):
    d = _ocr_words();d['text']=['DATE:','2031-08-21','2031-08-21'];d['top']=[310,310,770]
    _patch_ocr(monkeypatch,d)
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'expiry_date': 'mismatch'}}, {'expiry_date': '2031-08-21'})
    assert result['reason'] == 'mismatch_not_localized'


def test_masked_number_mismatch_is_not_guessed(monkeypatch):
    _patch_ocr(monkeypatch)
    result = localize_disputed_printed_fields(_image(),
        {'comparisons': {'document_number': 'mismatch'}}, {'document_number_masked': '*****3456'})
    assert result['regions_detected'] == 0
