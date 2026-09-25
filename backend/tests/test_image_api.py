"""Requires Flask + flask-cors: installed on user development machine."""
import io,os
import pytest
flask=pytest.importorskip('flask')
pytest.importorskip('flask_cors')
from PIL import Image
from app import app


def _image():
    buffer=io.BytesIO();Image.new('RGB',(64,64),'white').save(buffer,format='PNG')
    return buffer.getvalue()


def test_detector_endpoint_requires_token(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN','test-secret')
    client=app.test_client()
    assert client.post('/api/v1/detect/image',data={'image':(io.BytesIO(_image()),'test.png')}).status_code==401


def test_detector_endpoint_handles_corrupt_image(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN','test-secret')
    client=app.test_client()
    response=client.post('/api/v1/detect/image',headers={'Authorization':'Bearer test-secret'},data={'image':(io.BytesIO(b'bad image'),'test.png')})
    assert response.status_code==400


def test_detector_endpoint_returns_real_model_score(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN','test-secret')
    client=app.test_client()
    response=client.post('/api/v1/detect/image',headers={'Authorization':'Bearer test-secret'},data={'image':(io.BytesIO(_image()),'test.png')})
    assert response.status_code==200,response.json
    result=response.json['image_generation']
    assert result['model_version']=='community-forensics-2026-08-fullres-research-demo'
    assert isinstance(result['ai_generation_score'],float)
    assert result['research_only'] is True
