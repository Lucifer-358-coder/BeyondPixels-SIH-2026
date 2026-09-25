"""Isolated C2PA SDK worker: reads bounded image bytes from stdin, outputs a minimal JSON result."""
from __future__ import annotations

import io
import json
import sys


def main() -> dict:
    try:
        from c2pa import Context, Reader
    except ImportError:
        return {'status': 'unavailable', 'finding': 'sdk_not_installed',
                'manifest_present': None, 'validation_state': None, 'signer_trust': 'not_established',
                'method': 'c2pa_python_sdk_offline_v1', 'message': 'C2PA SDK is unavailable.'}
    if len(sys.argv) != 2 or sys.argv[1] not in ('image/jpeg', 'image/png'):
        raise ValueError('Unsupported format')
    raw = sys.stdin.buffer.read(8 * 1024 * 1024 + 1)
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise ValueError('Invalid length')
    context = Context.from_dict({'verify': {
        'verify_after_reading': True, 'verify_trust': True,
        'verify_timestamp_trust': True, 'remote_manifest_fetch': False,
        'ocsp_fetch': False,
    }})
    reader = Reader.try_create(sys.argv[1], io.BytesIO(raw), context=context)
    if reader is None:
        return {'status': 'not_found', 'finding': 'no_c2pa_manifest',
                'manifest_present': False, 'validation_state': None,
                'signer_trust': 'not_established', 'validation_issues': None,
                'method': 'c2pa_python_sdk_offline_v1',
                'message': 'No embedded C2PA manifest; absence does not establish authenticity or forgery.'}
    with reader:
        state = reader.get_validation_state()
        issues = reader.get_validation_results()
    # An SDK "Valid" state is a validation result, not the person's identity or
    # an authoritative passport authenticity result. Report trust separately.
    allowed_states = ('Trusted', 'Valid', 'Invalid')
    state = state if isinstance(state, str) and state in allowed_states else 'Unknown'
    if state == 'Unknown':
        return {'status': 'unavailable', 'finding': 'validation_state_unavailable',
                'manifest_present': True, 'validation_state': None,
                'signer_trust': 'not_established',
                'method': 'c2pa_python_sdk_offline_v1',
                'message': 'SDK did not return a recognized validation state; verification is inconclusive.'}
    issue_count = None
    if isinstance(issues, dict):
        # Only count explicitly recorded failed statuses; do not infer success
        # from a missing/unknown results schema.
        for key in ('failure', 'failures'):
            value = issues.get(key)
            if isinstance(value, list):
                issue_count = (issue_count or 0) + len(value)
    result = {
        'status': 'completed', 'finding': 'sdk_validation_' + state.lower(),
        'manifest_present': True, 'validation_state': state,
        'signer_trust': 'sdk_reported_trusted' if state == 'Trusted' else 'not_established',
        'validation_issues': issue_count,
        'method': 'c2pa_python_sdk_offline_v1',
        'message': ('C2PA SDK checked embedded signature, asset binding and configured trust offline. '
                    'Offline checking cannot retrieve remote manifests or live certificate revocation. '
                    'C2PA does not establish document genuineness or the depicted person\'s identity.'),
    }
    return result


if __name__ == '__main__':
    try:
        payload = main()
    except Exception:
        payload = {'status': 'unavailable', 'finding': 'verification_error',
                   'manifest_present': None, 'validation_state': None,
                   'signer_trust': 'not_established', 'method': 'c2pa_python_sdk_offline_v1',
                   'message': 'C2PA SDK could not validate the file; no cryptographic result established.'}
    sys.stdout.write(json.dumps(payload, separators=(',', ':')))
