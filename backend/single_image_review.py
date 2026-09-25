"""Single-upload document field-discrepancy localization (research prototype).

Highlights *where a reliably parsed printed field disagrees with passport MRZ*.
It is not standalone pixel-forgery, photo-replacement, or security-feature detection.
No OCR text, identity data, or cropped images are returned or persisted.
"""
from __future__ import annotations

import re

_FIELD_LABELS = {
    'expiry_date': re.compile(r'^(?:EXPIRY|EXPIRATION)$', re.I),
    'date_of_birth': re.compile(r'^(?:BIRTH|DOB)$', re.I),
    'document_number': re.compile(r'^NUMBER:?$', re.I),
}


def _unassessed(reason: str, message: str, *, status: str = 'not_assessed') -> dict:
    return {
        'status': status,
        'finding': 'inconclusive',
        'method': 'single_image_correlated_field_location_v1',
        'regions_detected': 0, 'top_regions': [], 'overlay_available': False,
        'reason': reason, 'message': message,
        'limitation': 'Not standalone pixel tampering, portrait replacement, or proof of forgery.',
    }


def _normalized(value: object) -> str:
    return re.sub(r'[^A-Z0-9]', '', value.upper()) if isinstance(value, str) else ''


def localize_disputed_printed_fields(image, consistency: dict, printed_fields: dict) -> dict:
    """Return boxes only for independently established MRZ/OCR discrepancies.

    OCR geometry must *re-find* the existing printed observation, in an explicit
    labelled line and with adequate confidence, before displaying any rectangle.
    All abstentions are review-safe; matching fields are not proof of genuineness.
    """
    comparisons = consistency.get('comparisons', {}) if isinstance(consistency, dict) else {}
    mismatches = [key for key, status in comparisons.items()
                  if status == 'mismatch' and key in _FIELD_LABELS]
    if not mismatches:
        return _unassessed('no_correlated_mismatch',
                           'No independently comparable printed-field mismatch to locate. Visual alteration has not been assessed.')
    try:
        import pytesseract
        from pytesseract import Output
        raw = pytesseract.image_to_data(image, config='--psm 6', output_type=Output.DICT, timeout=10)
    except Exception:
        return _unassessed('geometry_ocr_unavailable',
                           'Could not reliably locate the disputed printed field; review the original document.')
    width, height = image.size
    if width < 100 or height < 100 or width * height > 16_000_000:
        return _unassessed('image_geometry_unsupported', 'Image geometry is unsuitable for localized review.')
    groups: dict[tuple, list[dict]] = {}
    for i, token in enumerate(raw.get('text', [])):
        if not isinstance(token, str) or not token.strip():
            continue
        try:
            confidence = float(raw['conf'][i])
            word = dict(text=token.strip(), conf=confidence,
                        x=int(raw['left'][i]), y=int(raw['top'][i]),
                        w=int(raw['width'][i]), h=int(raw['height'][i]))
            group = tuple(raw[field][i] for field in ('page_num', 'block_num', 'par_num', 'line_num'))
        except (ValueError, TypeError, IndexError, KeyError):
            continue
        if word['w'] <= 0 or word['h'] <= 0 or word['conf'] < 45:
            continue
        groups.setdefault(group, []).append(word)
    found = []
    for key in mismatches:
        # Currently only expiry and DOB can be safely matched to a full value.
        # The document number is masked, so locating a suffix alone would be unsafe.
        field_key = 'expiry_date' if key == 'expiry_date' else 'date_of_birth' if key == 'date_of_birth' else None
        value = _normalized(printed_fields.get(field_key)) if field_key else ''
        if not value or not 6 <= len(value) <= 16:
            continue
        for words in groups.values():
            words.sort(key=lambda item: item['x'])
            if not words or min(w['y'] for w in words) >= height * .72:
                continue  # never confuse the MRZ with printed text
            texts = [_normalized(w['text']) for w in words]
            # Expiry must be expressly labelled in the same OCR line.
            if key == 'expiry_date' and not any(t in ('EXPIRY', 'EXPIRATION') for t in texts[:5]):
                continue
            if key == 'date_of_birth' and not ('DOB' in texts[:6] or
                    all(t in texts[:6] for t in ('DATE', 'BIRTH'))):
                continue
            for i, word in enumerate(words):
                joined = ''
                for j in range(i, min(i + 4, len(words))):
                    joined += texts[j]
                    if joined == value:
                        chosen = words[i:j + 1]
                        if not chosen or min(w['conf'] for w in chosen) < 55:
                            break
                        x0 = max(0, min(w['x'] for w in chosen) - 5)
                        y0 = max(0, min(w['y'] for w in chosen) - 5)
                        x1 = min(width, max(w['x'] + w['w'] for w in chosen) + 5)
                        y1 = min(height, max(w['y'] + w['h'] for w in chosen) + 5)
                        if x1 > x0 and y1 > y0:
                            found.append((key, dict(
                                x=round(x0 / width, 6), y=round(y0 / height, 6),
                                width=round((x1 - x0) / width, 6),
                                height=round((y1 - y0) / height, 6),
                                field=key, observation='printed_vs_mrz_mismatch',
                            )))
                        break
                    if not value.startswith(joined):
                        break
            if any(k == key for k, _ in found):
                break
    unique = []
    seen = set()
    for key, box in found:
        if key not in seen:
            seen.add(key)
            unique.append(box)
    if not unique:
        return _unassessed('mismatch_not_localized',
                           'Field mismatch exists, but the printed location could not be confirmed independently.')
    return {
        'status': 'completed', 'finding': 'correlated_field_discrepancy',
        'method': 'single_image_correlated_field_location_v1',
        'regions_detected': len(unique), 'top_regions': unique[:4],
        'overlay_available': True, 'image_width': width, 'image_height': height,
        'reason': 'corroborated_ocr_mrz_discrepancy',
        'message': 'Boxes locate OCR/MRZ-disputed printed fields for review; they do NOT identify pixel edits or prove forgery.',
        'limitation': 'Not standalone pixel tampering, portrait replacement, or proof of forgery.',
    }
