"""TD3 display-field tests with fictional, non-identifying specimen text."""
from mrz import inspect_passport_mrz
from ocr_fields import extract_mrz_display_fields
from test_mrz import LINE1, LINE2


def test_valid_mrz_fields_are_conservative_and_bounded():
    text = LINE1 + '\n' + LINE2
    validation = inspect_passport_mrz(text)
    fields = extract_mrz_display_fields(text, validation)
    assert fields['holder_name'] == 'ERIKSSON, ANNA MARIA'
    assert fields['nationality_code'] == 'UTO'
    assert fields['date_of_birth_yy_mm_dd'] == '74-08-12'
    assert fields['document_number_masked'] == '*****02C3'
    assert fields['expiry_date'] == '2012-04-15'
    assert 'L898902C3' not in str(fields)
    assert '1974' not in str(fields)  # No century inferred from YYMMDD.


def test_failed_number_check_hides_number_but_keeps_independent_fields():
    text = LINE1 + '\n' + 'M' + LINE2[1:]
    validation = inspect_passport_mrz(text)
    fields = extract_mrz_display_fields(text, validation)
    assert validation['checks']['document_number'] is False
    assert 'document_number_masked' not in fields
    assert fields['holder_name'] == 'ERIKSSON, ANNA MARIA'
    assert fields['nationality_code'] == 'UTO'
    assert fields['date_of_birth_yy_mm_dd'] == '74-08-12'


def test_unreadable_mrz_or_unchecked_validation_never_invents_fields():
    assert extract_mrz_display_fields('photo only', {'document_type': 'passport'}) == {}
    assert extract_mrz_display_fields(LINE1 + '\n' + LINE2, {'document_type': 'unknown'}) == {}
    assert extract_mrz_display_fields(LINE1 + '\n' + LINE2, {'document_type': 'passport'}) == {
        'holder_name': 'ERIKSSON, ANNA MARIA', 'nationality_code': 'UTO'
    }
