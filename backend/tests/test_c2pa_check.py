"""C2PA boundary tests; SDK cryptography is exercised separately on Windows."""
from pathlib import Path
from types import SimpleNamespace
import json
import c2pa_check


def test_no_sdk_returns_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(c2pa_check, 'ROOT', tmp_path)
    monkeypatch.setattr(c2pa_check, 'WORKER', tmp_path / 'missing.py')
    monkeypatch.delenv('BEYONDPIXELS_C2PA_PYTHON', raising=False)
    out = c2pa_check.verify_content_credentials(b'fake jpeg', 'JPEG')
    assert out['status'] == 'unavailable' and out['manifest_present'] is None


def test_sdk_response_no_raw_manifest(monkeypatch, tmp_path):
    exe = tmp_path / 'python.exe'; exe.write_bytes(b'placeholder')
    worker = tmp_path / 'worker.py'; worker.write_bytes(b'placeholder')
    monkeypatch.setenv('BEYONDPIXELS_C2PA_PYTHON', str(exe))
    monkeypatch.setattr(c2pa_check, 'WORKER', worker)
    payload = dict(status='completed', finding='sdk_validation_invalid', manifest_present=True,
                   validation_state='Invalid', signer_trust='not_established', raw_manifest='SECRET',
                   message='Cryptographic verification returned invalid')
    monkeypatch.setattr(c2pa_check.subprocess, 'run', lambda *args, **kwargs:
                        SimpleNamespace(returncode=0, stdout=json.dumps(payload).encode()))
    out = c2pa_check.verify_content_credentials(b'fake jpeg', 'JPEG')
    assert out['validation_state'] == 'Invalid'
    assert 'raw_manifest' not in out


def test_worker_timeout_abstains(monkeypatch, tmp_path):
    import subprocess
    exe = tmp_path / 'python.exe'; exe.write_bytes(b'x')
    worker = tmp_path / 'worker.py'; worker.write_bytes(b'x')
    monkeypatch.setenv('BEYONDPIXELS_C2PA_PYTHON', str(exe))
    monkeypatch.setattr(c2pa_check, 'WORKER', worker)
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired('python', 15)
    monkeypatch.setattr(c2pa_check.subprocess, 'run', timed_out)
    assert c2pa_check.verify_content_credentials(b'fake jpeg', 'JPEG')['status'] == 'unavailable'


def test_no_fake_forgery_verdict():
    assert c2pa_check.verify_content_credentials(b'', 'JPEG')['status'] == 'not_assessed'
