"""Bounded, offline, subprocess-isolated C2PA SDK validation.

No marker scans, no remote manifest/network fetching, no test trust bypasses.
No metadata field is interpreted as proof of authenticity or an actual identity.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
WORKER = ROOT / 'c2pa_worker.py'


def _unavailable(message: str):
    return {'status': 'unavailable', 'finding': 'verification_unavailable',
            'manifest_present': None, 'validation_state': None, 'signer_trust': 'not_established',
            'method': 'c2pa_python_sdk_offline_v1', 'message': message}


def verify_content_credentials(data: bytes, fmt: str) -> dict:
    if fmt not in ('JPEG', 'PNG') or not data or len(data) > 8 * 1024 * 1024:
        return {'status': 'not_assessed', 'finding': 'unsupported_format_or_size',
                'manifest_present': None, 'validation_state': None, 'signer_trust': 'not_established',
                'method': 'c2pa_python_sdk_offline_v1',
                'message': 'C2PA evaluation only accepts bounded JPEG/PNG files.'}
    override = os.environ.get('BEYONDPIXELS_C2PA_PYTHON', '')
    if override:
        executable = Path(override)
    else:
        executable = ROOT / '.venv_c2pa' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not executable.is_file() or not WORKER.is_file():
        return _unavailable('C2PA SDK worker is not installed; no signature verification performed.')
    try:
        result = subprocess.run(
            [str(executable), '-I', str(WORKER), 'image/jpeg' if fmt == 'JPEG' else 'image/png'],
            input=data, capture_output=True, timeout=15, cwd=str(ROOT), check=False,
        )
        if result.returncode or len(result.stdout) > 16384:
            return _unavailable('C2PA worker exited unsuccessfully; no verification result.')
        output = json.loads(result.stdout.decode('utf-8'))
        if not isinstance(output, dict) or output.get('status') not in ('completed', 'not_found', 'unavailable'):
            return _unavailable('Invalid C2PA worker response; no verification result.')
        # Whitelist output properties; never expose raw manifests, signer IDs, or URLs.
        permitted = ('status', 'finding', 'manifest_present', 'validation_state',
                     'signer_trust', 'method', 'message', 'validation_issues')
        return {k: output[k] for k in permitted if k in output}
    except (subprocess.TimeoutExpired, OSError, UnicodeError, ValueError, TypeError):
        return _unavailable('C2PA verification timed out or failed; no result established.')
