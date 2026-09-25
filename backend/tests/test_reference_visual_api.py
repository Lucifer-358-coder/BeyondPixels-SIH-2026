"""Reference-only localization in document endpoint, no media model, no PII."""
from __future__ import annotations

import io

import pytest
pytest.importorskip('flask')
pytest.importorskip('flask_cors')
import numpy as np
from PIL import Image
import app as application


def _png(array):
    out = io.BytesIO()
    Image.fromarray(array).save(out, format='PNG')
    return out.getvalue()


def _setup(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'reference-only-fixture-token')
    monkeypatch.setattr(application, 'detect_image', lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('Document invoked media detector')))
    monkeypatch.setattr(application, 'analyze_deepfake', lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('Document invoked deepfake detector')))
    monkeypatch.setattr(application, 'extract_text', lambda _: {'status': 'unavailable', 'text': ''})
    return application.app.test_client()


def _pair():
    before = np.full((240, 400, 3), 255, dtype=np.uint8)
    after = before.copy()
    after[62:93, 210:245] = 0
    return _png(before), _png(after)


def _post(client, current, ref=None, token='reference-only-fixture-token'):
    data = {'image': (io.BytesIO(current), 'current.png')}
    if ref is not None:
        data['reference_image'] = (io.BytesIO(ref), 'reference.png')
    return client.post('/v1/screen', headers={'Authorization': 'Bearer ' + token},
                       data=data, content_type='multipart/form-data')


def test_document_with_reference_detects_region_without_media_models(monkeypatch):
    client = _setup(monkeypatch)
    before, after = _pair()
    result = _post(client, after, before)
    assert result.status_code == 200, result.get_json()
    body = result.get_json()
    region = body['tampering_localization']
    assert region['status'] == 'completed' and region['overlay_available'] is True
    assert region['finding'] == 'localized_pixel_differences'
    assert region['regions_detected'] >= 1
    assert body['image_generation']['status'] == 'not_applicable'
    assert body['deepfake']['status'] == 'not_implemented'
    assert before[:200] not in str(body).encode('utf8')


def test_document_without_reference_abstains(monkeypatch):
    client = _setup(monkeypatch)
    before, _ = _pair()
    result = _post(client, before)
    assert result.status_code == 200
    assert result.get_json()['tampering_localization']['reason'] == 'reference_required'


def test_missing_or_invalid_reference_is_rejected_without_processing(monkeypatch):
    client = _setup(monkeypatch)
    before, _ = _pair()
    response = _post(client, before, b'not an image')
    assert response.status_code == 400
    assert 'reference' in response.get_json()['error'].lower()


def test_wrong_token_rejected_before_reference_processing(monkeypatch):
    client = _setup(monkeypatch)
    before, after = _pair()
    response = _post(client, after, before, token='wrong')
    assert response.status_code == 401
