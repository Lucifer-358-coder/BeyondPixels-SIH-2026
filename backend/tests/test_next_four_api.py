"""Local API boundaries: no data needed beyond synthetic PNG and fake credentials."""
from io import BytesIO
from unittest.mock import patch
from PIL import Image
from app import app


def _png():
    out = BytesIO()
    Image.new('RGB', (240, 160), 'white').save(out, 'PNG')
    return out.getvalue()


def test_new_features_opt_in_and_document_isolation(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'fake-local-test-token')
    with patch('app.extract_text', return_value={'status': 'unavailable', 'text': ''}), \
         patch('app.detect_image', side_effect=AssertionError('must not run')), \
         patch('app.analyze_deepfake', side_effect=AssertionError('must not run')):
        r = app.test_client().post('/v1/screen',
            headers={'Authorization': 'Bearer fake-local-test-token'},
            data={'image': (BytesIO(_png()), 'fictional.png'),
                  'authorized_reference_images': [(BytesIO(_png()), 'fixture.png')]},
            content_type='multipart/form-data')
    assert r.status_code == 200
    body = r.get_json()
    assert body['image_similarity']['candidates'][0]['observation'] == 'exact_file_duplicate'
    assert body['evidence_report']['status'] == 'completed'
    assert body['image_generation']['status'] == 'not_applicable'
    assert body['ocr']['raw_text_returned'] is False
    assert body['review_ref'].count('.') == 1


def test_audit_auth_and_action_enum(monkeypatch, tmp_path):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN', 'fake-local-test-token')
    monkeypatch.setenv('BEYONDPIXELS_AUDIT_DB', str(tmp_path / 'local_audit.sqlite3'))
    from review_audit import create_review_ref
    ref = create_review_ref('fake-local-test-token')
    client = app.test_client()
    action = {'review_ref': ref, 'action': 'follow_up_required'}
    assert client.post('/v1/review', json=action).status_code == 401
    headers = {'Authorization': 'Bearer fake-local-test-token'}
    assert client.post('/v1/review', json={**action, 'raw_ocr': 'SECRET'}, headers=headers).status_code == 400
    assert client.post('/v1/review', json={**action, 'action': 'approve_travel'}, headers=headers).status_code == 400
    result = client.post('/v1/review', json=action, headers=headers)
    assert result.status_code == 201
    assert 'SECRET' not in str(result.get_json())
    observed = client.get('/v1/review/' + ref, headers=headers)
    assert observed.status_code == 200
    assert observed.get_json()['events'][0]['action'] == 'follow_up_required'
