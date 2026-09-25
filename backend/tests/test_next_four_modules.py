"""Self-contained bounded research tests; no token, faces, real identities or external network."""
from io import BytesIO
from PIL import Image, ImageDraw

from authorized_similarity import review_authorized_references
from review_report import build_review_report
from review_audit import create_review_ref, valid_review_ref, record_action, fetch_events


def _image(shift=0):
    img = Image.new('RGB', (240, 160), '#eee')
    draw = ImageDraw.Draw(img)
    for col in range(20):
        left = col * 11 + shift
        draw.rectangle((left, 20 + col % 5 * 11, left + 4, 145), fill='#163957')
    b = BytesIO()
    img.save(b, 'PNG')
    return img, b.getvalue()


def test_opt_in_only_exact_and_no_persistence():
    image, source = _image()
    empty = review_authorized_references(image, source, [])
    assert empty['status'] == 'not_assessed'
    exact = review_authorized_references(image, source, [(image, source)])
    assert exact['candidates'] == [{'reference_index': 1, 'observation': 'exact_file_duplicate', 'distance_bits': 0}]
    assert 'bytes' not in str(exact) and 'identity' in exact['message']


def test_different_aspect_and_flat_image_abstain():
    image, source = _image()
    different = Image.new('RGB', (128, 450), 'red')
    b = BytesIO();different.save(b, 'PNG')
    result = review_authorized_references(image, source, [(different, b.getvalue())])
    assert result['status'] == 'completed'
    assert result['candidates'] == []
    flat = Image.new('RGB', (200, 200), 'white'); b = BytesIO(); flat.save(b, 'PNG')
    result2 = review_authorized_references(flat, b.getvalue(), [(image, source)])
    assert result2['candidates'] == []


def test_reject_unbounded_reference_count():
    import pytest
    img, raw = _image()
    with pytest.raises(ValueError):
        review_authorized_references(img, raw, [(img, raw)] * 5)


def test_report_does_not_copy_pii_or_invent_verdict():
    data = {'status': 'inconclusive', 'finding': 'no_supported_indicator',
            'raw_text': 'SECRET_PERSON_99999999'}
    report = build_review_report(ocr=data, mrz=data, consistency=data,
                                 localization=data, tampering=data, portrait=data,
                                 face=data, duplicates=data, c2pa=data)
    assert len(report['observations']) == 9
    assert 'SECRET_PERSON' not in str(report)
    assert 'identity' in report['message']


def test_audit_only_accepts_signed_ref_and_enum_without_pii(tmp_path, monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_AUDIT_DB', str(tmp_path / 'audit.sqlite3'))
    ref = create_review_ref('local-demo-test-token')
    assert valid_review_ref('local-demo-test-token', ref)
    assert not valid_review_ref('wrong-token', ref)
    assert not valid_review_ref('local-demo-test-token', ref[:-1] + '0' if ref[-1] != '0' else ref[:-1] + '1')
    event = record_action(ref, 'follow_up_required')
    assert event['status'] == 'recorded'
    assert 'token' not in str(event)
    assert fetch_events(ref)[0]['action'] == 'follow_up_required'
    import pytest
    with pytest.raises(ValueError): record_action(ref, 'approve_travel')
