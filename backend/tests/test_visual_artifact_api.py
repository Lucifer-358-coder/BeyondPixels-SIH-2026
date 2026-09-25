"""Document-only route: safe JPEG diagnostics and PNG abstention, never a verdict."""
from __future__ import annotations
from io import BytesIO

import pytest
pytest.importorskip('flask')
pytest.importorskip('flask_cors')
from PIL import Image
import app as application


def _call(monkeypatch, fmt):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'synthetic-artifact-test-token')
    monkeypatch.setattr(application, 'extract_text', lambda image: {'status':'unavailable', 'text':''})
    monkeypatch.setattr(application, 'detect_image', lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('Document invoked AI media classifier')))
    monkeypatch.setattr(application, 'analyze_deepfake', lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('Document invoked face classifier')))
    im = Image.new('RGB', (512, 512), 'white')
    b = BytesIO();im.save(b, format=fmt)
    response = application.app.test_client().post(
        '/v1/screen', headers={'Authorization':'Bearer synthetic-artifact-test-token'},
        data={'image':(BytesIO(b.getvalue()),'fictional.'+fmt.lower())},
        content_type='multipart/form-data')
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_jpeg_endpoint_is_independent_and_never_calls_it_forged(monkeypatch):
    result = _call(monkeypatch, 'JPEG')
    visual = result['visual_artifact_review']
    assert visual['status'] == 'completed'
    assert visual['finding'] == 'diagnostic_only'
    assert visual['standalone_forgery_detection'] is False
    assert result['image_generation']['status'] == 'not_applicable'
    assert result['deepfake']['status'] == 'not_implemented'


def test_png_endpoint_abstains_without_claiming_clean(monkeypatch):
    result = _call(monkeypatch, 'PNG')
    visual = result['visual_artifact_review']
    assert visual['status'] == 'not_assessed'
    assert visual['reason'] == 'jpeg_only'
    assert visual['standalone_forgery_detection'] is False


def test_capabilities_disclose_visual_diagnostic_limit():
    modules = application.app.test_client().get('/v1/capabilities').get_json()['modules']
    assert modules['visual_artifact_review']['standalone_forgery_detection'] is False
    assert modules['visual_artifact_review']['requires_reference_image'] is False
