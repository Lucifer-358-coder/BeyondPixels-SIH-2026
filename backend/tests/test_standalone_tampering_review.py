from standalone_tampering_review import assess_standalone_tampering_review as assess

def test_no_signal_is_inconclusive():
    r=assess({}, {}, {}, {}, {}, {})
    assert r['status']=='inconclusive' and r['forgery_detected'] is None

def test_structural_plus_visual_requires_review():
    r=assess({'comparisons':{'expiry_date':'mismatch'}},{}, {'status':'completed','regions_detected':1},
             {}, {'status':'completed','finding':'repeated_texture_candidate','candidate_regions':1}, {})
    assert r['status']=='review_required'
    assert r['finding']=='multiple_independent_indicators'

def test_metadata_software_tag_is_not_tampering_evidence():
    r=assess({}, {}, {}, {}, {}, {'finding':'software_tag_present'})
    assert r['evidence_count']==0 and r['software_metadata_observed'] is True
