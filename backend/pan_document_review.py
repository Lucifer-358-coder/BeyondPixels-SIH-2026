"""Indian PAN-card OCR observations, not issuer/identity verification.

No original image, raw OCR transcript, unmasked PAN or biometric data is stored.
Only literal PAN-shaped strings are recognized; OCR characters are never repaired.
"""
from __future__ import annotations

from datetime import date, datetime
import re

PAN_PATTERN = re.compile(r'(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])')
PAN_CONTEXT = re.compile(r'INCOME\s*TAX|PERMANENT\s+ACCOUNT|\bPAN\s*(?:CARD|NO\.?|NUMBER|APPLICATION)\b', re.I)
DOB_LABEL = re.compile(r'\b(?:DATE\s*OF\s*BIRTH|DOB|D\.?O\.?B\.?)\b\s*[:\-]?\s*', re.I)
DATE_PATTERN = re.compile(r'(?<!\d)(?:\d{1,2}[/.-]\d{1,2}[/.-]\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:JAN(?:UARY)?|FEB(?:RUARY)?|MAR(?:CH)?|APR(?:IL)?|MAY|JUN(?:E)?|JUL(?:Y)?|AUG(?:UST)?|SEP(?:T(?:EMBER)?)?|OCT(?:OBER)?|NOV(?:EMBER)?|DEC(?:EMBER)?)\s+\d{4})(?!\d)', re.I)


def _literal_date(value):
    value = re.sub(r'\s+', ' ', value.strip())
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d',
                '%d %b %Y', '%d %B %Y'):
        try:
            return datetime.strptime(value.title(), fmt).date()
        except ValueError:
            pass
    return None


def _dob_observations(text):
    lines = [line.strip()[:180] for line in text.splitlines()[:100]]
    values = []
    for i, line in enumerate(lines):
        label = DOB_LABEL.search(line)
        if not label:
            continue
        # Look on the labelled line, or the immediately following line only.
        for candidate in (line[label.end():], lines[i + 1] if i + 1 < len(lines) else ''):
            found = DATE_PATTERN.search(candidate)
            if found:
                values.append(found.group())
                break
    return values


def _ocr_fallback(image, initial_text):
    """Second layout pass only for likely PAN or weak original OCR; bounded 12 s."""
    if not (PAN_CONTEXT.search(initial_text) or len(initial_text.strip()) < 25):
        return ''
    if not hasattr(image, 'size') or min(image.size) < 80:
        return ''
    try:
        import pytesseract
        from PIL import ImageOps
        work = ImageOps.grayscale(image)
        if max(work.size) < 1100:
            scale = min(3.0, 1400.0 / max(work.size))
            if scale > 1.01:
                from PIL import Image
                work = work.resize((round(work.width * scale), round(work.height * scale)), Image.Resampling.LANCZOS)
        return pytesseract.image_to_string(work, config='--psm 11', timeout=12)[:12000]
    except Exception:
        return ''


def inspect_pan_document(image, ocr_text: str, printed_fields: dict) -> tuple[dict, dict]:
    """Return (evidence, enriched safe fields). No PAN without PAN-card context."""
    text = (ocr_text if isinstance(ocr_text, str) else '')[:12000]
    fields = dict(printed_fields if isinstance(printed_fields, dict) else {})
    alternative = _ocr_fallback(image, text)
    if not (PAN_CONTEXT.search(text) or PAN_CONTEXT.search(alternative)):
        return ({'status': 'not_assessed', 'document_type': 'unknown',
                 'finding': 'pan_document_not_identified',
                 'checks': {}, 'message': 'No sufficiently clear PAN-document context in OCR.'}, fields)

    observations = [s for s in (text, alternative) if s]
    numbers = {match.group() for s in observations for match in PAN_PATTERN.finditer(s.upper())}
    raw_dobs = {s.strip().upper() for obs in observations for s in _dob_observations(obs)}
    parsed = {_literal_date(raw) for raw in raw_dobs}
    parsed.discard(None)
    invalid_dob = bool(raw_dobs) and (len(parsed) != len(raw_dobs) or any(d > date.today() or d.year < 1900 for d in parsed))

    checks = {'pan_number_format': 'not_assessed', 'date_of_birth_format': 'not_assessed',
              'issuer_database': 'not_available', 'document_authenticity': 'not_assessed'}
    if len(numbers) == 1:
        number = next(iter(numbers))
        fields['document_number_masked'] = '*' * 6 + number[-4:]
        checks['pan_number_format'] = 'format_observed'
    elif len(numbers) > 1:
        fields.pop('document_number_masked', None)
        checks['pan_number_format'] = 'ambiguous_ocr'

    if invalid_dob or len(parsed) > 1:
        fields.pop('date_of_birth', None)
        checks['date_of_birth_format'] = 'ambiguous_or_invalid_ocr'
    elif len(parsed) == 1:
        normalized = next(iter(parsed)).isoformat()
        prior = fields.get('date_of_birth')
        # Do not replace a conflicting OCR observation silently.
        if prior and _literal_date(str(prior)) != next(iter(parsed)):
            fields.pop('date_of_birth', None)
            checks['date_of_birth_format'] = 'ambiguous_ocr'
        else:
            fields['date_of_birth'] = normalized
            checks['date_of_birth_format'] = 'format_observed'

    issues = any(v in ('ambiguous_ocr', 'ambiguous_or_invalid_ocr') for v in checks.values())
    count = sum(v == 'format_observed' for v in checks.values())
    status = 'review_required' if issues else 'completed' if count == 2 else 'inconclusive'
    finding = ('ocr_observations_need_review' if issues else
               'pan_and_dob_formats_observed' if count == 2 else
               'partial_pan_format_observations' if count else 'no_pan_fields_read')
    return ({'status': status, 'document_type': 'pan_card', 'finding': finding,
             'method': 'literal_pan_pattern_and_labelled_dob_ocr_v1',
             'checks': checks, 'fields_observed': count,
             'message': 'PAN-shaped text and labelled birth date are OCR format observations only; no issuing-authority, identity or authenticity check was performed.'}, fields)
