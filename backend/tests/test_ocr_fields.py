from ocr_fields import extract_labelled_fields


def test_labelled_fields_and_document_number_redaction():
    data = extract_labelled_fields('Name: ALEX SAMPLE\nDocument Number: TEST123456\nDate of Birth: 15 JAN 2000\nNationality: TEST\nExpiry Date: 31 DEC 2030')
    assert data == {
        'name': 'ALEX SAMPLE', 'document_number_masked': '******3456',
        'date_of_birth': '15 JAN 2000', 'nationality': 'TEST',
        'expiry_date': '31 DEC 2030',
    }
    assert 'TEST123456' not in str(data)


def test_unlabelled_and_empty_text_not_invented():
    assert extract_labelled_fields('P<UTOSAMPLE<<ALEX<TEST\n') == {}
    assert extract_labelled_fields('') == {}


def test_long_lines_do_not_leak_data():
    assert extract_labelled_fields('Name: ' + 'A' * 200) == {}
