from services import inspect_stai


def test_no_stai_config_does_not_fabricate_result(monkeypatch):
    monkeypatch.delenv('STAI_ANALYZE_URL', raising=False)
    result = inspect_stai(b'fake-image', 'image/png')
    assert result['status'] == 'not_configured'
    assert result['ai_generated'] is None
    assert result['reported_confidence'] is None
