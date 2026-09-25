import io
from unittest.mock import patch
from PIL import Image
from app import app

def png():
    b=io.BytesIO(); Image.new('RGB',(300,300),'white').save(b,format='PNG'); return b.getvalue()

def test_screen_exposes_bounded_reviews(monkeypatch):
    monkeypatch.setenv('BEYONDPIXELS_DEMO_TOKEN','x')
    with patch('app.extract_text',return_value={'status':'unavailable','text':''}), \
         patch('app.assess_standalone_tampering_review',return_value={'status':'inconclusive','finding':'no_supported_indicator'}), \
         patch('app.review_portrait_replacement',return_value={'status':'not_assessed','finding':'comparison_unavailable'}):
        r=app.test_client().post('/v1/screen',headers={'Authorization':'Bearer x'},data={'image':(io.BytesIO(png()),'a.png')})
    assert r.status_code==200
    j=r.get_json()
    assert j['standalone_tampering_review']['finding']=='no_supported_indicator'
    assert j['portrait_replacement_review']['finding']=='comparison_unavailable'
