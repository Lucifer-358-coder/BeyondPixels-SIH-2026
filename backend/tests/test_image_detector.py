from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from image_detector import detect_image,_model_bundle
from media import InvalidMedia
from stai_features import FEATURE_NAMES,extract_stai_features


def png_bytes(gray=127):
    out=BytesIO();Image.new('RGB',(64,64),(gray,gray,gray)).save(out,format='PNG');return out.getvalue()


def test_detector_inconclusive_is_not_assumed_authentic():
    result=detect_image(png_bytes())
    assert result['status']=='completed'
    assert result['scope']=='whole_image_generation_only'
    assert result['research_only'] is True
    assert result['source_attribution']['status']=='not_supported'
    assert result['provenance']['status']=='not_checked'
    assert result['ai_generated'] in (True,False,None)
    assert result['decision'] in ('likely_ai_generated','likely_not_ai_generated','inconclusive')
    if result['decision']=='inconclusive':assert result['ai_generated'] is None
    assert 0<=result['ai_generation_score']<=1
    assert 'authentic' not in result['decision']


def test_rejects_non_image_bytes():
    with pytest.raises(InvalidMedia): detect_image(b'not a png')


def test_features_match_training_order_and_are_finite():
    vec,notes=extract_stai_features(png_bytes())
    assert vec.shape==(1,5)
    assert len(FEATURE_NAMES)==5
    assert np.isfinite(vec).all()
    assert notes['perspective_inconclusive'] is True


def test_thresholds_from_separate_validation_not_hardcoded_inference():
    _,metadata=_model_bundle()
    assert metadata['status']=='research_only_not_validated_for_identity_documents'
    assert 'validation_metrics' in metadata and 'saved_cifake_test_metrics' in metadata
    assert metadata['low_not_ai_threshold'] is None  # not validated to issue a not-AI claim
