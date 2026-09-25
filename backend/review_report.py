"""A bounded, machine-readable evidence summary; never an identity/fraud verdict."""
from __future__ import annotations


def build_review_report(*, ocr: dict, mrz: dict, consistency: dict,
                        localization: dict, tampering: dict, portrait: dict,
                        face: dict, duplicates: dict, c2pa: dict) -> dict:
    observations = []
    for label, item in (
        ('OCR', ocr), ('MRZ consistency', mrz), ('Printed-field consistency', consistency),
        ('Disputed printed-field locations', localization),
        ('Standalone tampering indicators', tampering), ('Portrait visibility', portrait),
        ('Optional photo comparison', face), ('Authorized reference similarity', duplicates),
        ('Offline content credentials', c2pa),
    ):
        # Status and finding codes only; no OCR text, passport numbers or photos.
        observations.append({'check': label, 'status': str(item.get('status', 'not_assessed'))[:48],
                             'finding': str(item.get('finding', 'not_assessed'))[:80]})
    follow_up = [x['check'] for x in observations
                 if x['status'] in ('review_required', 'checksum_mismatch', 'expired', 'invalid_format')]
    return {'status': 'completed', 'scope': 'evidence_summary_for_manual_review_only',
            'observations': observations, 'manual_review_items': follow_up,
            'message': 'Missing evidence and inconclusive checks are not passes. '
                       'This report cannot establish identity, document authenticity, or fraud.'}
