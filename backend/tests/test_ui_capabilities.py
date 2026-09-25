"""Isolated contract checks; no model, document image, or network required."""
from ui_capabilities import ui_capabilities


def test_declared_features_are_bounded():
    value = ui_capabilities()
    assert value['research_only'] is True
    assert value['criterion_selection_supported'] is False
    modules = value['modules']
    assert modules['ocr']['available'] is True
    assert modules['mrz']['available'] is True
    assert modules['image_generation']['available'] is True
    assert modules['image_similarity']['available'] is True
    assert modules['image_similarity']['persistent_gallery'] is False
    assert modules['review_audit']['available'] is True
    assert modules['provenance']['available'] is True
    assert modules['provenance']['scope'] == 'embedded_file_metadata_observations_only'
    assert modules['provenance']['cryptographic_provenance_validation'] is False
    assert isinstance(modules['face_verification']['available'], bool)
    assert modules['face_verification']['identity_verification'] is False
    assert modules['face_verification']['requires_optional_consent_face_photo'] is True
    assert modules['tampering_localization']['available'] is True
    assert modules['tampering_localization']['requires_reference_image'] is True
    assert modules['tampering_localization']['standalone_forgery_detection'] is False
    assert isinstance(modules['deepfake']['available'], bool)
    assert isinstance(modules['face_detection']['available'], bool)
    assert modules['deepfake']['scope'] == 'frontal_face_crops_research'
    assert value['input']['max_bytes'] == 8 * 1024 * 1024


def test_final_review_capabilities_are_bounded():
    m=ui_capabilities()['modules']
    assert m['standalone_tampering_review']['standalone_pixel_forgery_classifier'] is False
    assert m['portrait_replacement_review']['portrait_replacement_detection'] is False
