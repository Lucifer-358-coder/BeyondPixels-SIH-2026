from io import BytesIO
import numpy as np
from PIL import Image
from expanded_forensics import extract_exploratory_descriptors
from image_detector import detect_image


def png(data):
    stream = BytesIO()
    Image.fromarray(data.astype('uint8'), 'RGB').save(stream, format='PNG')
    return stream.getvalue()


def test_constant_image_finite_and_no_claims():
    result = extract_exploratory_descriptors(png(np.full((64, 64, 3), 127)))
    assert result['status'] == 'completed'
    assert result['used_for_prediction'] is False
    assert len(result['descriptors']) == 5
    assert all(np.isfinite(x) and x >= 0 for x in result['descriptors'].values())
    assert result['descriptors']['high_band_energy_fraction'] == 0


def test_deterministic_and_different_texture():
    rng = np.random.default_rng(314)
    noisy = png(rng.integers(0, 256, (80, 80, 3), dtype=np.uint8))
    a = extract_exploratory_descriptors(noisy)
    assert a == extract_exploratory_descriptors(noisy)
    flat = extract_exploratory_descriptors(png(np.full((80, 80, 3), 128)))
    assert a['descriptors']['high_band_energy_fraction'] > flat['descriptors']['high_band_energy_fraction']


def test_no_change_to_frozen_classifier_score(monkeypatch):
    # Exploratory module failure must not change original SVM inference.
    raw = png(np.full((64, 64, 3), 128))
    baseline = detect_image(raw)
    import expanded_forensics
    def unavailable(_):
        raise RuntimeError('experimental module offline')
    monkeypatch.setattr(expanded_forensics, 'extract_exploratory_descriptors', unavailable)
    fallback = detect_image(raw)
    assert baseline['ai_generation_score'] == fallback['ai_generation_score']
    assert baseline['decision'] == fallback['decision']
    assert fallback['additional_forensic_observations'] == {'status': 'unavailable', 'used_for_prediction': False}


def test_tiny_image_abstains_from_descriptors():
    result = extract_exploratory_descriptors(png(np.full((8, 8, 3), 128)))
    assert result['status'] == 'insufficient_resolution'
    assert result['descriptors'] == {}
