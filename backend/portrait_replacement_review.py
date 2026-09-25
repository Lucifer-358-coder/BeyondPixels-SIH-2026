"""Optional portrait-to-photo inconsistency review.

Uses an operator-supplied authorized face photo. This cannot prove portrait
replacement or identity; it only interprets the already-computed similarity
relative to the OpenCV Zoo demonstration threshold as a research observation.
"""
from __future__ import annotations
from portrait_face_comparison import EXAMPLE_COSINE_THRESHOLD


def review_portrait_replacement(face_comparison: dict | None) -> dict:
    face = face_comparison if isinstance(face_comparison, dict) else {}
    if face.get('status') != 'completed' or not isinstance(face.get('cosine_similarity'), (int,float)):
        return {'status':'not_assessed','finding':'comparison_unavailable',
                'method':'optional_portrait_photo_inconsistency_review_v1',
                'reference_threshold':EXAMPLE_COSINE_THRESHOLD,
                'portrait_replacement_detected':None,'identity_verified':False,
                'message':'A usable document portrait and authorized comparison photo are required; no replacement conclusion.'}
    score=float(face['cosine_similarity'])
    below=score < EXAMPLE_COSINE_THRESHOLD
    return {'status':'review_required' if below else 'completed',
            'finding':'portrait_photo_inconsistency_candidate' if below else 'similarity_above_reference_threshold',
            'method':'optional_portrait_photo_inconsistency_review_v1',
            'cosine_similarity':round(score,5),'reference_threshold':EXAMPLE_COSINE_THRESHOLD,
            'portrait_replacement_detected':None,'identity_verified':False,
            'message':('Similarity falls below the OpenCV Zoo example threshold; review the document portrait and authorized photo manually. '
                       if below else
                       'Similarity is above the OpenCV Zoo example threshold. This does not verify identity or exclude portrait replacement.'),
            'limitation':'The reference threshold is not calibrated for photographed identity documents or this deployment.'}
