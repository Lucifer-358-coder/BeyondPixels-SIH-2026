"""Experimental TD1 (3x30) and TD2 (2x36) OCR/MRZ consistency.

No identity authentication, country-specific ID support, OCR checksum correction,
or full identity number output. Long document-number variants abstain.
"""
from __future__ import annotations

import re
from PIL import Image, ImageOps
from mrz import check_digit, _expiry, find_td3_lines
from datetime import date

MRZ_CHARS = re.compile(r'[A-Z0-9<]+\Z')


def _lines(text: str):
    lines = [''.join(line.upper().split()) for line in text.splitlines()]
    # Require exact, adjacent, photographed MRZ rows; never pad/truncate lines.
    for i in range(len(lines)):
        if (i + 3 <= len(lines) and all(len(line) == 30 and MRZ_CHARS.fullmatch(line)
                                      for line in lines[i:i+3])
                and lines[i][0] in 'ACI' and lines[i][1] in '<ACI'
                and re.fullmatch(r'[A-Z<]{3}', lines[i][2:5])):
            return 'td1', lines[i:i+3]
        if (i + 2 <= len(lines) and all(len(line) == 36 and MRZ_CHARS.fullmatch(line)
                                      for line in lines[i:i+2])
                and lines[i][0] in 'ACI' and lines[i][1] in '<ACI'
                and re.fullmatch(r'[A-Z<]{3}', lines[i][2:5])):
            return 'td2', lines[i:i+2]
    return None


def _mask_number(raw: str) -> str:
    value = raw.replace('<', '')
    return '*' * max(0, len(value) - 4) + value[-4:] if value else ''


def inspect_additional_mrz(text: str) -> dict:
    pair = _lines(text)
    if pair is None:
        return {'status': 'not_detected', 'document_type': 'unknown', 'checks': {},
                'message': 'No confidently read TD1 or TD2 machine-readable zone.'}
    form, rows = pair
    if form == 'td1':
        first, middle, _last = rows
        # TD1: 1-based checksum source: L1[6:30]+L2[1:7]+L2[9:15]+L2[19:29].
        # Long document numbers have variant layout; do not misread filler as a failed checksum.
        number = first[5:14]
        if first[14] == '<':
            return {'status': 'date_inconclusive', 'document_type': 'td1_id_card',
                    'mrz_format': 'TD1', 'checks': {},
                    'message': 'Extended TD1 document number is not supported; review manually.'}
        birth, birth_check = middle[0:6], middle[6]
        expiry, expiry_check = middle[8:14], middle[14]
        composite_source = first[5:30] + middle[0:7] + middle[8:15] + middle[18:29]
        digits = {'document_number': (number, first[14]),
                  'birth_date': (birth, birth_check),
                  'expiry_date': (expiry, expiry_check),
                  'composite': (composite_source, middle[29])}
        kind, source = 'td1_id_card', number
    else:
        _first, second = rows
        number = second[0:9]
        if second[9] == '<':
            return {'status': 'date_inconclusive', 'document_type': 'td2_travel_document',
                    'mrz_format': 'TD2', 'checks': {},
                    'message': 'Extended TD2 document number is not supported; review manually.'}
        birth, birth_check = second[13:19], second[19]
        expiry, expiry_check = second[21:27], second[27]
        composite_source = second[0:10] + second[13:20] + second[21:35]
        digits = {'document_number': (number, second[9]),
                  'birth_date': (birth, birth_check),
                  'expiry_date': (expiry, expiry_check),
                  'composite': (composite_source, second[35])}
        kind, source = 'td2_travel_document', number
    try:
        checks = {name: check_digit(value) == digit for name, (value, digit) in digits.items()}
    except ValueError:
        return {'status': 'invalid_format', 'document_type': kind, 'mrz_format': form.upper(), 'checks': {},
                'message': 'MRZ contains an invalid character.'}
    expiry_iso = _expiry(expiry)
    status = ('checksum_mismatch' if not all(checks.values()) else
              'date_inconclusive' if expiry_iso is None else
              'expired' if date.fromisoformat(expiry_iso) < date.today() else 'checks_passed')
    return {'status': status, 'document_type': kind, 'mrz_format': form.upper(),
            'document_number_masked': _mask_number(source),
            'expiry_date': expiry_iso, 'checks': checks,
            'message': 'MRZ check digits assess internal consistency only; not document authenticity.'}


def inspect_extra_from_image(image: Image.Image, ordinary_ocr: str) -> dict:
    found = inspect_additional_mrz(ordinary_ocr)
    if found['status'] != 'not_detected' or find_td3_lines(ordinary_ocr) is not None:
        return found
    # One bounded independent OCR attempt, no checksum-guided corrections.
    # Existing TD3 OCR is unchanged; this only runs if TD3 was not detected.
    try:
        import pytesseract
        gray = ImageOps.autocontrast(image.convert('L'))
        h = gray.height
        if gray.width < 300 or h < 150:
            return found
        crop = gray.crop((0, int(h * 0.30), gray.width, h))
        text = pytesseract.image_to_string(
            crop, config='--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<',
            timeout=8,
        )
        return inspect_additional_mrz(text)
    except Exception:
        return found
