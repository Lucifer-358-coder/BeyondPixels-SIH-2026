"""Contract tests: do not assert model accuracy or require downloading weights."""
import io
from unittest.mock import patch

import cv2
import numpy as np

from deepfake_service import analyze_deepfake
from app import app


def _image():
    ok, image = cv2.imencode('.png', np.full((128, 128, 3), 128, dtype=np.uint8))
    assert ok
    return image.tobytes()


def test_missing_model_never_gives_authentic_verdict():
    with patch('deepfake_service.deepfake_ready', return_value=False):
        result = analyze_deepfake(_image())
    assert result['status'] == 'unavailable'
    assert result['decision'] is None


def test_no_face_is_not_assessed():
    with patch('deepfake_service.deepfake_ready', return_value=True), patch(
        'cv2.CascadeClassifier'
    ) as fake:
        fake.return_value.empty.return_value = False
        fake.return_value.detectMultiScale.return_value = []
        result = analyze_deepfake(_image())
    assert result['status'] == 'not_assessed'
    assert result['decision'] is None
    assert result['face_count'] == 0


def test_image_endpoint_runs_separate_deepfake(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'contract-token')
    monkeypatch.setattr('app.detect_image', lambda image, content_already_validated: {
        'status': 'completed', 'decision': 'inconclusive'})
    monkeypatch.setattr('app.analyze_deepfake', lambda image: {
        'status': 'not_assessed', 'decision': None, 'face_count': 0})
    response = app.test_client().post('/api/v1/detect/image',
        headers={'Authorization': 'Bearer contract-token'},
        data={'image': (io.BytesIO(_image()), 'sample.png')},
        content_type='multipart/form-data')
    assert response.status_code == 200
    body = response.get_json()
    assert body['image_generation']['status'] == 'completed'
    assert body['deepfake']['status'] == 'not_assessed'


def test_document_endpoint_never_runs_deepfake(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'contract-token')
    monkeypatch.setattr('app.analyze_deepfake', lambda image: (_ for _ in ()).throw(
        AssertionError('Document screening must not invoke deepfake detector')))
    monkeypatch.setattr('app.extract_text', lambda image: {'status': 'unavailable', 'text': ''})
    monkeypatch.setattr('app.detect_image', lambda image, content_already_validated: {
        'status': 'completed', 'decision': 'inconclusive', 'ai_generated': None})
    response = app.test_client().post('/v1/screen',
        headers={'Authorization': 'Bearer contract-token'},
        data={'image': (io.BytesIO(_image()), 'sample.png')},
        content_type='multipart/form-data')
    assert response.status_code == 200
    assert response.get_json()['deepfake']['status'] == 'not_implemented'


def test_model_score_is_independent_of_generation_score(monkeypatch, tmp_path):
    import types
    from deepfake_service import analyze_deepfake
    from unittest.mock import patch
    class OneFace:
        def empty(self): return False
        def detectMultiScale(self, *args, **kwargs): return [(20, 20, 70, 70)]
    payload = types.SimpleNamespace(returncode=0, stdout='{"scores": [0.92]}')
    with patch('deepfake_service.deepfake_ready', return_value=True), \
         patch('cv2.CascadeClassifier', return_value=OneFace()), \
         patch('deepfake_service.subprocess.run', return_value=payload):
        value = analyze_deepfake(_image())
    assert value['status'] == 'completed'
    assert value['faces'][0]['decision'] == 'possible_manipulation'
    assert value['faces'][0]['fake_score'] == 0.92


def test_worker_failure_returns_unavailable_not_fake_score():
    import types
    from unittest.mock import patch
    class OneFace:
        def empty(self): return False
        def detectMultiScale(self, *args, **kwargs): return [(20, 20, 70, 70)]
    bad = types.SimpleNamespace(returncode=1, stdout='')
    with patch('deepfake_service.deepfake_ready', return_value=True), \
         patch('cv2.CascadeClassifier', return_value=OneFace()), \
         patch('deepfake_service.subprocess.run', return_value=bad):
        value = analyze_deepfake(_image())
    assert value['status'] == 'unavailable'
    assert value['decision'] is None
