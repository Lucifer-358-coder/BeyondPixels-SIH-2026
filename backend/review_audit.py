"""Operator-initiated local demo review log; NO PII, images or tokens stored.

Not tamper-proof, does not establish user roles or production authentication.
"""
from __future__ import annotations

import hashlib
from contextlib import closing
import hmac
import os
from pathlib import Path
import re
import secrets
import sqlite3
from datetime import datetime, timezone

VALID_ACTIONS = frozenset({'reviewed', 'follow_up_required', 'inconclusive'})
REF_FORMAT = re.compile(r'^[0-9a-f]{32}\.[0-9a-f]{32}$')


def create_review_ref(token: str) -> str:
    nonce = secrets.token_hex(16)
    mac = hmac.new(token.encode('utf-8'), nonce.encode('ascii'), hashlib.sha256).hexdigest()[:32]
    return f'{nonce}.{mac}'


def valid_review_ref(token: str, ref: object) -> bool:
    if not isinstance(ref, str) or not REF_FORMAT.fullmatch(ref) or not token:
        return False
    nonce, signature = ref.split('.')
    actual = hmac.new(token.encode('utf-8'), nonce.encode('ascii'), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(signature, actual)


def _database() -> Path:
    specified = os.getenv('BEYONDPIXELS_AUDIT_DB')
    if specified:
        return Path(specified)
    return Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.local' / 'share') / 'BeyondPixels' / 'review_audit.sqlite3'


def _connect():
    path = _database()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.execute('CREATE TABLE IF NOT EXISTS review_events ('
                 'event_id TEXT PRIMARY KEY, review_ref TEXT NOT NULL, action TEXT NOT NULL, '
                 'recorded_at TEXT NOT NULL)')
    return conn


def record_action(review_ref: str, action: str) -> dict:
    if action not in VALID_ACTIONS:
        raise ValueError('Unsupported review action')
    event = {'event_id': secrets.token_hex(16), 'review_ref': review_ref,
             'action': action, 'recorded_at': datetime.now(timezone.utc).isoformat()}
    with closing(_connect()) as conn:
        with conn:
            conn.execute('INSERT INTO review_events VALUES (:event_id,:review_ref,:action,:recorded_at)', event)
    return {'status': 'recorded', 'event_id': event['event_id'], 'action': action,
            'recorded_at': event['recorded_at'], 'scope': 'local_demo_review_log_no_identity_or_image_data'}


def fetch_events(review_ref: str) -> list[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute('SELECT event_id,action,recorded_at FROM review_events '
                            'WHERE review_ref=? ORDER BY recorded_at DESC LIMIT 50', (review_ref,)).fetchall()
    return [dict(zip(('event_id', 'action', 'recorded_at'), row)) for row in rows]
