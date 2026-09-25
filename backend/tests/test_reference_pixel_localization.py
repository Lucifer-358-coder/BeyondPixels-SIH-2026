"""No image history, no model, no false standalone tamper verdict."""
from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from tampering_localization import localize_document_pixel_differences as compare


def _png(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_without_reference_abstains():
    image = Image.new('RGB', (250, 160), 'white')
    result = compare(image, _png(image), None, None)
    assert result['status'] == 'not_assessed'
    assert result['reason'] == 'reference_required'
    assert result['overlay_available'] is False


def test_same_pixels_never_means_genuine():
    image = Image.new('RGB', (250, 160), 'white')
    data = _png(image)
    result = compare(image, data, image.copy(), data)
    assert result['finding'] == 'no_detected_pixel_difference'
    assert result['regions_detected'] == 0
    assert 'authenticity' in result['message']


def test_localized_changed_pixels_and_normalized_boxes():
    reference = Image.new('RGB', (640, 400), 'white')
    current = reference.copy()
    pixels = np.asarray(current).copy()
    pixels[110:137, 221:258] = (8, 8, 8)
    current = Image.fromarray(pixels)
    result = compare(current, _png(current), reference, _png(reference))
    assert result['status'] == 'completed', result
    assert result['finding'] == 'localized_pixel_differences'
    assert result['regions_detected'] >= 1
    assert result['overlay_available'] is True
    box = result['top_regions'][0]
    assert box['x'] < 221 / 640 < box['x'] + box['width']
    assert box['y'] < 110 / 400 < box['y'] + box['height']
    assert 0 <= box['x'] < 1 and 0 <= box['width'] <= 1
    assert 'image_bytes' not in str(result)


def test_reference_dimension_mismatch_abstains():
    source = Image.new('RGB', (250, 160), 'white')
    other = Image.new('RGB', (251, 160), 'white')
    result = compare(source, _png(source), other, _png(other))
    assert result['status'] == 'not_assessed'
    assert result['reason'] == 'dimensions_differ'


def test_wrong_reference_must_abstain_instead_of_forgery_verdict():
    source = Image.new('RGB', (250, 160), 'white')
    other = Image.new('RGB', (250, 160), 'black')
    result = compare(source, _png(source), other, _png(other))
    assert result['status'] == 'not_assessed'
    assert result['reason'] == 'alignment_or_reference_uncertain'


def test_png_required_not_jpeg_recompression_artifacts():
    source = Image.new('RGB', (250, 160), 'white')
    jpeg = BytesIO()
    source.save(jpeg, format='JPEG')
    result = compare(source, jpeg.getvalue(), source, _png(source))
    assert result['status'] == 'not_assessed'
    assert result['reason'] == 'png_pair_required'


def test_real_fictional_fixture_pair_when_available():
    from pathlib import Path
    sample_dir = Path(__file__).parents[3] / 'samples'
    before = sample_dir / 'fictional_passport_matching.png'
    after = sample_dir / 'fictional_passport_changed_expiry.png'
    if not before.is_file() or not after.is_file():
        import pytest
        pytest.skip('Separate fictional fixtures not present in backend workspace')
    ref_bytes, current_bytes = before.read_bytes(), after.read_bytes()
    with Image.open(before) as ref_image, Image.open(after) as current_image:
        ref, current = ref_image.convert('RGB'), current_image.convert('RGB')
    result = compare(current, current_bytes, ref, ref_bytes)
    assert result['status'] == 'completed', result
    assert result['regions_detected'] > 0
    assert all(0 <= r['x'] <= 1 and 0 <= r['y'] <= 1 for r in result['top_regions'])
