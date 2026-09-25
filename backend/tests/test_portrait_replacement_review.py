from portrait_replacement_review import review_portrait_replacement

def test_no_comparison_abstains():
    r=review_portrait_replacement({'status':'not_assessed'})
    assert r['status']=='not_assessed' and r['portrait_replacement_detected'] is None

def test_below_reference_threshold_requires_review_not_verdict():
    r=review_portrait_replacement({'status':'completed','cosine_similarity':0.10})
    assert r['status']=='review_required'
    assert r['finding']=='portrait_photo_inconsistency_candidate'
    assert r['portrait_replacement_detected'] is None and r['identity_verified'] is False

def test_above_reference_threshold_is_not_identity_verification():
    r=review_portrait_replacement({'status':'completed','cosine_similarity':0.8})
    assert r['status']=='completed'
    assert r['identity_verified'] is False and r['portrait_replacement_detected'] is None
