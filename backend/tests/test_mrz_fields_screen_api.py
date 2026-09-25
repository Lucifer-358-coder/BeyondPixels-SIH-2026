"""API tests for a separate MRZ field source; raw data stays server-side."""
import io
import pytest
pytest.importorskip('flask')
pytest.importorskip('flask_cors')
from PIL import Image
import app as screening_app
from mrz import inspect_passport_mrz
from test_mrz import LINE1, LINE2


@pytest.mark.parametrize('invalid', [False, True])
def test_screen_mrz_fields_are_separate_and_redacted(monkeypatch, invalid):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'local-test')
    monkeypatch.setattr(screening_app, 'extract_text', lambda image: {
        'status': 'completed', 'text': 'unlabelled text'
    })
    text = LINE1 + '\n' + ('M' + LINE2[1:] if invalid else LINE2)
    monkeypatch.setattr(screening_app, 'extract_td3_mrz', lambda image: {
        'status': 'detected', 'text': text
    })
    monkeypatch.setattr(screening_app, 'detect_image', lambda *args, **kwargs: {
        'status': 'completed', 'decision': 'inconclusive', 'ai_generated': None
    })
    buffer = io.BytesIO()
    Image.new('RGB', (64, 64), 'white').save(buffer, format='PNG')
    buffer.seek(0)
    response = screening_app.app.test_client().post(
        '/v1/screen', headers={'Authorization': 'Bearer local-test'},
        data={'image': (buffer, 'synthetic.png')},
    )
    assert response.status_code == 200, response.json
    ocr = response.json['ocr']
    assert ocr['mrz_extraction_status'] == 'detected'
    assert ocr['raw_text_returned'] is False
    assert ocr['fields'] == {}
    assert ocr['mrz_fields']['holder_name'] == 'ERIKSSON, ANNA MARIA'
    assert ocr['mrz_fields']['date_of_birth_yy_mm_dd'] == '74-08-12'
    assert ocr['mrz_fields_verified'] is False
    assert ('document_number_masked' in ocr['mrz_fields']) is (not invalid)
    assert 'L898902C3' not in response.get_data(as_text=True)
    assert LINE1 not in response.get_data(as_text=True)
    expected = 'checksum_mismatch' if invalid else 'expired'
    assert response.json['document_validation']['status'] == expected
