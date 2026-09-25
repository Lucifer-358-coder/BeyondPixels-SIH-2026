"""Conservative, bounded extraction of explicitly labelled OCR fields.

No raw OCR transcript or full document number is returned to the client.
These fields are unverified OCR observations, not verified identity facts.
"""
from __future__ import annotations

import re

_LABELS = {
    "name": (r"name", 80),
    "document_number_masked": (r"document\s*(?:number|no\.?|#)", 40),
    "date_of_birth": (r"(?:date\s*of\s*birth|dob)", 40),
    "nationality": (r"nationality", 40),
    "expiry_date": (r"(?:expiry\s*date|expiration\s*date|date\s*of\s*expiry)", 40),
}


def _mask(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]", "", value)
    return "*" * max(0, len(clean) - 4) + clean[-4:] if clean else ""


def extract_labelled_fields(text: str) -> dict[str, str]:
    """Capture only a single OCR line per recognized label, never guess fields."""
    result: dict[str, str] = {}
    for line in text.splitlines()[:100]:
        line = line.strip()[:220]
        for key, (label, limit) in _LABELS.items():
            if key in result:
                continue
            match = re.fullmatch(rf"\s*{label}\s*:\s*(.{{1,{limit}}})\s*", line, re.IGNORECASE)
            if not match:
                continue
            value = re.sub(r"\s+", " ", match.group(1)).strip()
            if not value:
                continue
            if key == "document_number_masked":
                value = _mask(value)
            if value:
                result[key] = value
    return result


def extract_mrz_display_fields(text: str, validation: dict) -> dict[str, str]:
    """Read-only, bounded display fields from an *already extracted* TD3 MRZ.

    A checksum is a consistency check, not identity verification. No century
    is inferred from a two-digit MRZ birth date, and the full document number
    never leaves this function. Do not repair OCR characters using checksums.
    """
    from mrz import find_td3_lines

    pair = find_td3_lines(text)
    if pair is None or validation.get("document_type") != "passport":
        return {}
    first, second = pair
    checks = validation.get("checks") or {}
    result: dict[str, str] = {}

    # TD3 line 1: P< + issuing code (3) + surname<<given<names + padding.
    raw_name = first[5:].rstrip("<")
    if "<<" in raw_name:
        surname, given = raw_name.split("<<", 1)
        surname = surname.replace("<", " ").strip()
        given = given.replace("<", " ").strip()
        if surname and len(surname) <= 39 and len(given) <= 39:
            result["holder_name"] = f"{surname}, {given}" if given else surname

    # Three-letter MRZ codes are displayed as codes, not guessed countries.
    nationality = second[10:13]
    if len(nationality) == 3 and nationality.isalpha() and nationality.isupper():
        result["nationality_code"] = nationality

    # Do not expose a field whose own check digit failed, even if it looks plausible.
    if checks.get("document_number") is True:
        masked = validation.get("document_number_masked")
        if isinstance(masked, str) and masked and len(masked) <= 16:
            result["document_number_masked"] = masked
    if checks.get("birth_date") is True:
        raw_birth = second[13:19]
        if raw_birth.isdigit() and len(raw_birth) == 6:
            result["date_of_birth_yy_mm_dd"] = (
                f"{raw_birth[:2]}-{raw_birth[2:4]}-{raw_birth[4:6]}"
            )
    if checks.get("expiry_date") is True:
        expiry = validation.get("expiry_date")
        if isinstance(expiry, str) and len(expiry) == 10:
            result["expiry_date"] = expiry
    return result
