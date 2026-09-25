from datetime import date
from mrz import check_digit, find_td3_lines, inspect_passport_mrz

# Standard fictional/example TD3 passport specimen, not a real identity.
LINE1 = 'P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<'
LINE2 = 'L898902C36UTO7408122F1204159ZE184226B<<<<<10'


def test_known_icao_check_digit():
    assert check_digit('L898902C3') == '6'


def test_example_passport_mrz_parses_and_checks():
    result = inspect_passport_mrz(LINE1 + '\n' + LINE2)
    assert result['document_type'] == 'passport'
    assert result['document_number_masked'].endswith('02C3')
    assert all(result['checks'].values()), result
    assert result['status'] == 'expired'


def test_modified_data_fails_checksum():
    tampered = 'M' + LINE2[1:]
    result = inspect_passport_mrz(LINE1 + '\n' + tampered)
    assert result['status'] == 'checksum_mismatch'
    assert result['checks']['document_number'] is False


def test_unreadable_mrz_is_not_declared_authentic():
    assert inspect_passport_mrz('photo only')['status'] == 'not_detected'


def test_invalid_characters_rejected():
    assert find_td3_lines(LINE1 + '\n' + LINE2.replace('UTO', 'UT@', 1)) is None
