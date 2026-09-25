"""Minimal, independently implemented ICAO TD3 passport MRZ checks.

This is a checksum and format validation utility, NOT a forgery detector.
It does not silently correct OCR characters in identity fields.
"""
from __future__ import annotations

from datetime import date
import re

WEIGHTS = (7, 3, 1)


def check_digit(value: str) -> str:
    total = 0
    for i, char in enumerate(value.upper()):
        if char == "<":
            number = 0
        elif "0" <= char <= "9":
            number = ord(char) - 48
        elif "A" <= char <= "Z":
            number = ord(char) - 55
        else:
            raise ValueError("Invalid MRZ character")
        total += number * WEIGHTS[i % 3]
    return str(total % 10)


def _expiry(raw: str) -> str | None:
    """Resolve YYMMDD only if an unambiguous, plausible expiry is found."""
    if not re.fullmatch(r"\d{6}", raw):
        return None
    yy, mm, dd = int(raw[:2]), int(raw[2:4]), int(raw[4:6])
    today = date.today()
    options = []
    for century in (1900, 2000, 2100):
        try:
            candidate = date(century + yy, mm, dd)
        except ValueError:
            continue
        if today.year - 25 <= candidate.year <= today.year + 20:
            options.append(candidate)
    return options[0].isoformat() if len(options) == 1 else None


def find_td3_lines(text: str) -> tuple[str, str] | None:
    """Find two unmodified 44-character OCR lines starting with P<."""
    lines = [line.strip().replace(" ", "") for line in text.upper().splitlines()]
    for first, second in zip(lines, lines[1:]):
        if (
            len(first) == len(second) == 44
            and first.startswith("P<")
            and re.fullmatch(r"[A-Z0-9<]{44}", first)
            and re.fullmatch(r"[A-Z0-9<]{44}", second)
        ):
            return first, second
    return None


def inspect_passport_mrz(text: str) -> dict:
    pair = find_td3_lines(text)
    if pair is None:
        return {
            "status": "not_detected",
            "document_type": "unknown",
            "checks": {},
            "message": "A two-line TD3 passport MRZ was not confidently extracted.",
        }
    first, second = pair
    try:
        checks = {
            "document_number": check_digit(second[0:9]) == second[9],
            "birth_date": check_digit(second[13:19]) == second[19],
            "expiry_date": check_digit(second[21:27]) == second[27],
            "optional_data": check_digit(second[28:42]) == second[42],
            "composite": check_digit(
                second[0:10] + second[13:20] + second[21:43]
            ) == second[43],
        }
    except ValueError:
        return {"status": "invalid_format", "document_type": "passport", "checks": {}}
    number = second[:9].replace("<", "")
    expiry_iso = _expiry(second[21:27])
    if not all(checks.values()):
        status = "checksum_mismatch"
    elif expiry_iso is None:
        status = "date_inconclusive"
    elif date.fromisoformat(expiry_iso) < date.today():
        status = "expired"
    else:
        status = "checks_passed"
    return {
        "status": status,
        "document_type": "passport",
        "document_number_masked": "*" * max(0, len(number) - 4) + number[-4:],
        "expiry_date": expiry_iso,
        "checks": checks,
        "message": "MRZ checks assess consistency, not document authenticity.",
    }
