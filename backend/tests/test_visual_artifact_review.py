"""Check honest abstentions and contracts; no accuracy assertions."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_artifact_review import review_jpeg_residuals


def test_png_abstains_and_never_calls_png_genuine():
    im = Image.new('RGB', (512, 512), 'white')
    b = BytesIO(); im.save(b, format='PNG')
    result = review_jpeg_residuals(im, b.getvalue())
    assert result['status'] == 'not_assessed'
    assert result['reason'] == 'jpeg_only'
    assert not result['standalone_forgery_detection']
    assert result['top_regions'] == []


def test_jpeg_diagnostic_never_claims_tampering():
    im = Image.new('RGB', (512, 512), 'white')
    d = ImageDraw.Draw(im)
    d.text((22, 50), 'SYNTHETIC TEST - NOT VALID ID', fill='black')
    d.rectangle((35, 120, 350, 260), outline='black', width=2)
    b = BytesIO(); im.save(b, format='JPEG', quality=89)
    result = review_jpeg_residuals(im, b.getvalue())
    assert result['status'] == 'completed'
    assert result['finding'] == 'diagnostic_only'
    assert not result['standalone_forgery_detection']
    assert result['overlay_available'] is False
    assert result['diagnostic_regions'] <= 3
    for region in result['top_regions']:
        for key in ('x','y','width','height'):
            assert 0 <= region[key] <= 1
    assert 'NOT tampering detections' in result['message']


def test_tiny_jpeg_abstains():
    im = Image.new('RGB', (32, 32), 'white')
    b = BytesIO(); im.save(b, format='JPEG')
    assert review_jpeg_residuals(im, b.getvalue())['reason'] == 'unsupported_image_geometry'


def test_invalid_bytes_abstain():
    im = Image.new('RGB', (512,512), 'white')
    assert review_jpeg_residuals(im, b'not an image')['status'] == 'not_assessed'
