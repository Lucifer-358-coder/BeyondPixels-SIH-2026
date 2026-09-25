"""Conservative printed-OCR-versus-TD3-MRZ checks for document review.

Not image-tampering detection, portrait examination, identity verification, or
proof of authenticity. Never returns personal field values or raw OCR text.
"""
from __future__ import annotations

from datetime import date
import re

_FIELDS = ("expiry_date", "date_of_birth", "document_number", "nationality_code")


def _iso_date(value: object) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if 1900 <= parsed.year <= 2099 else None


def _mrz_birth(value: object) -> str | None:
    # An MRZ birth date has a two-digit year. Never infer its century.
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}-\d{2}-\d{2}", value):
        return None
    yy, mm, dd = map(int, value.split("-"))
    if not any(_valid_date(century + yy, mm, dd) for century in (1900, 2000)):
        return None
    return value.replace("-", "")


def _valid_date(year: int, month: int, day: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _masked_suffix(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 20:
        return None
    # Only compare a four-character suffix previously masked by the OCR / MRZ
    # extractors. A matching suffix is weak evidence, never full-number proof.
    if not re.fullmatch(r"\*+[A-Za-z0-9]{4}", value):
        return None
    return value[-4:].upper()


def assess_document_consistency(
    printed_fields: dict | None,
    mrz_fields: dict | None,
    mrz_validation: dict | None,
    expiry_extraction: dict | None,
) -> dict:
    """Compare only reliably comparable observations, otherwise abstain.

    Output contains field names/statuses ONLY, no OCR text, DOB, or document
    number. A discrepancy calls for review, not a forgery conclusion.
    """
    printed = printed_fields if isinstance(printed_fields, dict) else {}
    machine = mrz_fields if isinstance(mrz_fields, dict) else {}
    validation = mrz_validation if isinstance(mrz_validation, dict) else {}
    expiry = expiry_extraction if isinstance(expiry_extraction, dict) else {}
    checks = validation.get("checks")
    checks = checks if isinstance(checks, dict) else {}
    passport = validation.get("document_type") == "passport"

    comparisons = {field: "not_compared" for field in _FIELDS}
    if passport:
        printed_expiry = _iso_date(printed.get("expiry_date"))
        mrz_expiry = _iso_date(machine.get("expiry_date"))
        # Conflicting/ambiguous printed OCR is not reliable enough for a
        # comparison. Missing expiry is not itself evidence of alteration.
        if expiry.get("status") not in ("conflict", "ambiguous") and checks.get("expiry_date") is True:
            if printed_expiry and mrz_expiry:
                comparisons["expiry_date"] = (
                    "match" if printed_expiry == mrz_expiry else "mismatch"
                )

        printed_birth = _iso_date(printed.get("date_of_birth"))
        mrz_birth = _mrz_birth(machine.get("date_of_birth_yy_mm_dd"))
        if printed_birth and mrz_birth and checks.get("birth_date") is True:
            comparisons["date_of_birth"] = (
                "match" if printed_birth.strftime("%y%m%d") == mrz_birth else "mismatch"
            )

        printed_number = _masked_suffix(printed.get("document_number_masked"))
        mrz_number = _masked_suffix(machine.get("document_number_masked"))
        if printed_number and mrz_number and checks.get("document_number") is True:
            comparisons["document_number"] = (
                "match" if printed_number == mrz_number else "mismatch"
            )

        printed_country = printed.get("nationality")
        mrz_country = machine.get("nationality_code")
        # Do not compare full country names with 3-letter codes or guess a
        # country-code mapping. Only two explicit three-letter codes qualify.
        if (isinstance(printed_country, str) and isinstance(mrz_country, str)
                and re.fullmatch(r"[A-Za-z]{3}", printed_country.strip())
                and re.fullmatch(r"[A-Z]{3}", mrz_country)):
            comparisons["nationality_code"] = (
                "match" if printed_country.strip().upper() == mrz_country else "mismatch"
            )

    failed_checksum = passport and any(value is False for value in checks.values())
    discrepancy = any(value == "mismatch" for value in comparisons.values())
    compared_count = sum(value != "not_compared" for value in comparisons.values())
    if discrepancy or failed_checksum or expiry.get("status") == "conflict":
        status = "review_required"
    elif compared_count:
        status = "no_comparable_discrepancy"
    else:
        status = "inconclusive"
    return {
        "status": status,
        "method": "printed_ocr_vs_passport_mrz_v1",
        "comparisons": comparisons,
        "fields_compared": compared_count,
        "mrz_checksum_issue": bool(failed_checksum),
        "printed_expiry_conflict": expiry.get("status") == "conflict",
        "message": (
            "Review flagged discrepancies against the original document. "
            "OCR and MRZ errors can cause false alarms."
            if status == "review_required" else
            "No discrepancies found among comparable OCR/MRZ fields; this does not prove authenticity."
            if status == "no_comparable_discrepancy" else
            "Insufficient reliable, comparable fields; document alteration was not assessed."
        ),
        "limitation": "No pixel-level tampering or portrait-replacement detection is performed.",
    }
