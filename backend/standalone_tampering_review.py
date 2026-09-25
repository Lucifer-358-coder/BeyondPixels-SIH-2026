"""Conservative multi-signal document tampering review.

This is a triage aggregator over independently bounded diagnostics. It is NOT a
validated pixel-forgery classifier and never returns a genuine/forged verdict.
"""
from __future__ import annotations


def _section(value):
    return value if isinstance(value, dict) else {}


def assess_standalone_tampering_review(consistency, mrz, single_image, jpeg_review, copy_move, metadata):
    consistency=_section(consistency); mrz=_section(mrz); single=_section(single_image)
    jpeg=_section(jpeg_review); copy=_section(copy_move); meta=_section(metadata)
    evidence=[]
    comparisons=_section(consistency.get('comparisons'))
    mismatches=sorted(k for k,v in comparisons.items() if v=='mismatch')
    if mismatches:
        evidence.append({'signal':'printed_vs_mrz_mismatch','strength':'corroborated','count':len(mismatches)})
    if mrz.get('status') in ('checksum_mismatch','invalid_format') or consistency.get('mrz_checksum_issue') is True:
        evidence.append({'signal':'mrz_integrity_issue','strength':'corroborated','count':1})
    if single.get('status')=='completed' and int(single.get('regions_detected') or 0)>0:
        evidence.append({'signal':'correlated_field_location','strength':'supporting','count':int(single.get('regions_detected') or 0)})
    if copy.get('status')=='completed' and copy.get('finding')=='repeated_texture_candidate':
        evidence.append({'signal':'repeated_texture_candidate','strength':'weak_visual','count':int(copy.get('candidate_regions') or 0)})
    if jpeg.get('status')=='completed' and int(jpeg.get('diagnostic_regions') or 0)>0:
        evidence.append({'signal':'jpeg_residual_regions','strength':'weak_visual','count':int(jpeg.get('diagnostic_regions') or 0)})
    # Metadata is intentionally NOT counted as tampering evidence. Editing software
    # tags can come from ordinary scanning/conversion workflows.
    software_tag_present = meta.get('finding') == 'software_tag_present'
    strong=sum(1 for e in evidence if e['strength']=='corroborated')
    visual=sum(1 for e in evidence if e['strength']=='weak_visual')
    supporting=sum(1 for e in evidence if e['strength']=='supporting')
    if strong and (visual or supporting):
        status='review_required'; finding='multiple_independent_indicators'
    elif strong:
        status='review_required'; finding='corroborated_structural_indicator'
    elif visual >= 2:
        status='inconclusive'; finding='multiple_weak_visual_indicators'
    elif evidence:
        status='inconclusive'; finding='single_weak_indicator'
    else:
        status='inconclusive'; finding='no_supported_indicator'
    return {
        'status':status,'finding':finding,'method':'bounded_multisignal_document_review_v1',
        'evidence_count':len(evidence),'evidence':evidence,
        'software_metadata_observed':bool(software_tag_present),
        'forgery_detected':None,'authenticity_established':False,
        'message':('Independent document signals require manual review. This is not a forged-document verdict.'
                   if status=='review_required' else
                   'Available single-image diagnostics are insufficient for a tampering conclusion.'),
        'limitation':'No validated standalone pixel-forgery classifier is used; weak image diagnostics can false alarm.',
    }
