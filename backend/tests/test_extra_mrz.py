"""Generated synthetic TD1/TD2 fixture checks. Fictional fields only."""
from pathlib import Path
import json
import pytest
from PIL import Image
from extra_mrz import inspect_additional_mrz, inspect_extra_from_image

SAMPLES = Path(__file__).resolve().parent / 'fixtures' / 'extra_mrz'

@pytest.mark.parametrize('filename,kind', [
    ('fictional_td1_id.png', 'td1_id_card'),
    ('fictional_td2_travel.png', 'td2_travel_document'),
])
def test_literal_mrz_no_correction(filename, kind):
    rows = json.loads((SAMPLES / 'mrz_rows.json').read_text())[filename]
    result = inspect_additional_mrz('\n'.join(rows))
    assert result['status'] == 'checks_passed'
    assert result['document_type'] == kind
    assert len(result['checks']) == 4 and all(result['checks'].values())
    assert result['document_number_masked'].startswith('*')
    assert 'TST123456' not in repr(result)

@pytest.mark.parametrize('filename,kind', [
    ('fictional_td1_id.png', 'td1_id_card'),
    ('fictional_td2_travel.png', 'td2_travel_document'),
])
def test_synthetic_ocr(filename, kind):
    from services import extract_text
    with Image.open(SAMPLES / filename) as image:
        ocr = extract_text(image)
        assert ocr['status'] == 'completed'
        result = inspect_extra_from_image(image, ocr['text'])
    assert result['document_type'] == kind, result
    assert result['status'] == 'checks_passed', result


def test_corrupted_check_digits_not_repaired():
    rows = json.loads((SAMPLES / 'mrz_rows.json').read_text())['fictional_td1_bad_digit.png']
    result = inspect_additional_mrz('\n'.join(rows))
    assert result['status'] == 'checksum_mismatch'
    assert result['checks']['document_number'] is False
    assert result['checks']['composite'] is False


def test_no_mrz_abstains():
    assert inspect_additional_mrz('NAME: TEST\nEXPIRY DATE: 2030-01-01')['status'] == 'not_detected'
