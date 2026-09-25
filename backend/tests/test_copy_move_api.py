"""Copy-move is document-only, independent of media scores and OCR status."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys

import pytest
pytest.importorskip('flask')
pytest.importorskip('flask_cors')
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as application
from test_copy_move_review import _fixture


def _screen(monkeypatch, image: Image.Image) -> dict:
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'copy-move-test-token')
    monkeypatch.setattr(application, 'extract_text', lambda _: {'status': 'unavailable', 'text': ''})
    monkeypatch.setattr(application, 'detect_image', lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError('Document invoked media classifier')))
    monkeypatch.setattr(application, 'analyze_deepfake', lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError('Document invoked deepfake classifier')))
    buf = BytesIO(); image.save(buf, 'PNG')
    response = application.app.test_client().post(
        '/v1/screen',
        headers={'Authorization':'Bearer copy-move-test-token'},
        data={'image': (BytesIO(buf.getvalue()), 'synthetic.png')},
        content_type='multipart/form-data',
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_document_route_exposes_candidate_without_media_inference(monkeypatch):
    result = _screen(monkeypatch, _fixture(True))
    assert result['copy_move_review']['finding'] == 'repeated_texture_candidate'
    assert result['copy_move_review']['general_forgery_detection'] is False
    assert result['image_generation']['status'] == 'not_applicable'
    assert result['deepfake']['status'] == 'not_implemented'


def test_document_route_plain_image_not_mislabelled_genuine(monkeypatch):
    result = _screen(monkeypatch, Image.new('RGB', (512, 512), 'white'))
    assert result['copy_move_review']['status'] == 'not_assessed'
    assert result['copy_move_review']['finding'] == 'inconclusive'
    modules = application.app.test_client().get('/v1/capabilities').get_json()['modules']
    assert modules['copy_move_review']['standalone_forgery_detection'] is False
