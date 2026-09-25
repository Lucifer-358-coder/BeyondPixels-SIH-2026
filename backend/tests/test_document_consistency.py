"""No personal values or raw OCR text leave conservative consistency review."""
from document_consistency import assess_document_consistency


def _review(printed=None, machine=None, checks=None, expiry_status="extracted", passport=True):
    return assess_document_consistency(
        printed or {}, machine or {},
        {"document_type": "passport" if passport else "unknown", "checks": checks or {}},
        {"status": expiry_status},
    )


def test_matching_iso_expiry_is_not_authenticity_verdict():
    result = _review({"expiry_date": "2030-01-01"}, {"expiry_date": "2030-01-01"}, {"expiry_date": True})
    assert result["status"] == "no_comparable_discrepancy"
    assert result["fields_compared"] == 1
    assert result["comparisons"]["expiry_date"] == "match"
    assert "does not prove authenticity" in result["message"]


def test_mismatching_printed_and_mrz_expiry_requires_review_without_exposing_dates():
    result = _review({"expiry_date": "2031-08-21"}, {"expiry_date": "2030-01-01"}, {"expiry_date": True})
    assert result["status"] == "review_required"
    assert result["comparisons"]["expiry_date"] == "mismatch"
    assert "2031" not in str(result) and "2030" not in str(result)
    assert "forged" not in str(result).lower()


def test_untrusted_mrz_expiry_checksum_is_not_compared():
    result = _review({"expiry_date": "2031-08-21"}, {"expiry_date": "2030-01-01"}, {"expiry_date": False})
    assert result["status"] == "review_required"
    assert result["mrz_checksum_issue"] is True
    assert result["comparisons"]["expiry_date"] == "not_compared"
    assert result["fields_compared"] == 0


def test_conflicting_or_ambiguous_ocr_does_not_claim_field_mismatch():
    for status in ("conflict", "ambiguous"):
        result = _review({"expiry_date": "2031-08-21"}, {"expiry_date": "2030-01-01"}, {"expiry_date": True}, status)
        assert result["comparisons"]["expiry_date"] == "not_compared"
        assert result["status"] == ("review_required" if status == "conflict" else "inconclusive")
        assert result["printed_expiry_conflict"] is (status == "conflict")


def test_birth_date_two_digit_year_no_century_inference():
    result = _review({"date_of_birth": "1974-08-12"}, {"date_of_birth_yy_mm_dd": "74-08-12"}, {"birth_date": True})
    assert result["comparisons"]["date_of_birth"] == "match"
    assert "1974" not in str(result)
    result = _review({"date_of_birth": "1974-08-13"}, {"date_of_birth_yy_mm_dd": "74-08-12"}, {"birth_date": True})
    assert result["comparisons"]["date_of_birth"] == "mismatch"
    assert result["status"] == "review_required"


def test_masked_document_number_only_compares_four_character_suffix():
    result = _review({"document_number_masked": "*****1234"},
                     {"document_number_masked": "*****5678"}, {"document_number": True})
    assert result["comparisons"]["document_number"] == "mismatch"
    assert "1234" not in str(result) and "5678" not in str(result)
    assert _review({"document_number_masked": "1234"},
                   {"document_number_masked": "*****5678"},
                   {"document_number": True})["fields_compared"] == 0


def test_only_compare_three_letter_nationality_codes():
    matched = _review({"nationality": " uto "}, {"nationality_code": "UTO"}, {})
    assert matched["comparisons"]["nationality_code"] == "match"
    skipped = _review({"nationality": "Utopia"}, {"nationality_code": "UTO"}, {})
    assert skipped["comparisons"]["nationality_code"] == "not_compared"


def test_unknown_document_missing_fields_and_bad_dates_abstain():
    assert _review({"expiry_date": "2031-01-01"}, {"expiry_date": "2030-01-01"},
                   {"expiry_date": True}, passport=False)["status"] == "inconclusive"
    result = _review({"expiry_date": "2031-02-29"}, {"expiry_date": "2030-01-01"},
                     {"expiry_date": True})
    assert result["status"] == "inconclusive"
    assert result["fields_compared"] == 0
    assert _review()["status"] == "inconclusive"


def test_absent_status_is_inconclusive_and_fixed_contract():
    out = assess_document_consistency(None, None, None, None)
    assert out["status"] == "inconclusive"
    assert set(out["comparisons"]) == {"expiry_date", "date_of_birth", "document_number", "nationality_code"}
    assert "pixel-level" in out["limitation"]
