"""API contract tests; skip when Flask is not installed in the test environment."""
import io

import pytest

pytest.importorskip('flask')
pytest.importorskip('flask_cors')
from PIL import Image
import app as screening_app


def test_screen_returns_labelled_fields_but_never_raw_text(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'local-test')
    monkeypatch.setattr(screening_app, 'extract_text', lambda image: {
        'status': 'completed', 'text': 'Name: ALEX SAMPLE\nDocument Number: TEST123456\n'
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
    assert response.status_code == 200
    body = response.get_json()
    assert body['ocr']['fields']['name'] == 'ALEX SAMPLE'
    assert body['ocr']['fields']['document_number_masked'] == '******3456'
    assert body['ocr']['raw_text_returned'] is False
    assert 'TEST123456' not in response.get_data(as_text=True)
