"""Conservative, synthetic-only copy-move diagnostic checks (not accuracy tests)."""
from __future__ import annotations
from io import BytesIO
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from copy_move_review import review_copy_move


def _fixture(duplicate: bool) -> Image.Image:
    rng = np.random.default_rng(123)
    pixels = rng.integers(0, 256, (640, 800, 3), dtype=np.uint8)
    background = cv2.GaussianBlur(pixels, (13, 13), 0)
    if duplicate:
        crop = pixels[50:180, 65:195].copy()
        background[60:190, 70:200] = crop
        background[340:470, 460:590] = crop
    return Image.fromarray(background)


def test_plain_textured_image_does_not_generate_candidate():
    result = review_copy_move(_fixture(False))
    assert result['finding'] in ('no_candidate_localized', 'inconclusive')
    assert result['top_regions'] == []
    assert result['general_forgery_detection'] is False


def test_two_explicitly_copied_textures_generate_candidate_png():
    result = review_copy_move(_fixture(True))
    assert result['status'] == 'completed'
    assert result['finding'] == 'repeated_texture_candidate'
    assert result['candidate_regions'] >= 1
    assert len(result['top_regions']) >= 2
    assert result['overlay_available'] is True
    for box in result['top_regions']:
        for key in ('x', 'y', 'width', 'height'):
            assert 0 <= box[key] <= 1
    assert result['general_forgery_detection'] is False


def test_jpeg_recompression_does_not_remove_obvious_synthetic_copy():
    image = _fixture(True)
    buf = BytesIO()
    image.save(buf, 'JPEG', quality=93)
    buf.seek(0)
    decoded = Image.open(buf)
    result = review_copy_move(decoded)
    assert result['finding'] == 'repeated_texture_candidate'


def test_uniform_image_abstains_not_claims_authenticity():
    result = review_copy_move(Image.new('RGB', (512, 512), 'white'))
    assert result['status'] == 'not_assessed'
    assert result['finding'] == 'inconclusive'
    assert result['overlay_available'] is False


def test_small_image_abstains():
    assert review_copy_move(Image.new('RGB', (64, 64)))['reason'] == 'unsupported_geometry'
