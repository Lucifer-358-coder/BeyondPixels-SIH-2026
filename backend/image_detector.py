"""Research-only BeyondPixels AI-image classifier with validated abstention contract.

Scores classify *whole-image generation* in a narrow CIFAKE domain. They do not
establish that a passport, face, text field, or identity is genuine. Never load
an untrusted pickle; this model is bundled as part of our own audited build.
"""
from __future__ import annotations
import hashlib
import json
import math
import pickle
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from media import open_document_image

MODEL_DIR = Path(__file__).resolve().parent / 'models'

@lru_cache(maxsize=1)
def _model_bundle():
    manifest = json.loads((MODEL_DIR/'beyondpixels_cifake_baseline.json').read_text(encoding='utf-8'))
    model_bytes=(MODEL_DIR/'beyondpixels_cifake_baseline.pkl').read_bytes()
    if hashlib.sha256(model_bytes).hexdigest()!=manifest['model_sha256']:
        raise ValueError('Bundled model checksum mismatch')
    model=pickle.loads(model_bytes)  # bundled trusted artifact ONLY; checksum is not a signature
    from stai_features import FEATURE_NAMES
    if tuple(manifest['feature_order'])!=FEATURE_NAMES:
        raise ValueError('Model and feature order mismatch')
    if list(model.classes_) != [0, 1]:
        raise ValueError('Unexpected model class order')
    low=manifest['low_not_ai_threshold']
    high=manifest['high_ai_threshold']
    if low is not None and not 0<=low<=1:raise ValueError('Invalid not-AI threshold')
    if high is not None and not 0<=high<=1:raise ValueError('Invalid AI threshold')
    if low is not None and high is not None and low>=high:
        raise ValueError('Invalid threshold ordering')
    return model,manifest


def detect_image(image_bytes: bytes, *, content_already_validated: bool=False) -> dict:
    """Return observational class score, abstaining outside validation cutoffs.

    Do not pass content_already_validated=True with untrusted unvalidated bytes.
    API route always calls open_document_image before passing bytes here.
    """
    started=perf_counter()
    if not content_already_validated:
        open_document_image(image_bytes)
    model,meta=_model_bundle()
    from stai_features import extract_stai_features
    features,observations=extract_stai_features(image_bytes)
    score=float(model.predict_proba(features)[0,1])
    if not math.isfinite(score) or not 0<=score<=1:
        raise ValueError('Invalid model score')
    lo=meta['low_not_ai_threshold'];hi=meta['high_ai_threshold']
    decision='inconclusive'
    if lo is not None and score<=lo:
        decision='likely_not_ai_generated'
    elif hi is not None and score>=hi:
        decision='likely_ai_generated'
    # Exploratory descriptors are isolated from the frozen 5-feature SVM.
    # Errors here must not change the established classifier result.
    try:
        from expanded_forensics import extract_exploratory_descriptors
        research_descriptors = extract_exploratory_descriptors(image_bytes)
    except Exception:
        research_descriptors = {'status': 'unavailable', 'used_for_prediction': False}
    return {
        'additional_forensic_observations': research_descriptors,
        'status':'completed',
        'decision':decision,
        'ai_generated': True if decision=='likely_ai_generated' else (False if decision=='likely_not_ai_generated' else None),
        'ai_generation_score':round(score,4),
        'not_ai_generation_score':round(1-score,4),
        'score_interpretation':'CIFAKE-trained model score; not probability of document authenticity or fraud',
        'thresholds':{'not_ai_max':lo,'ai_min':hi},
        'model_version':meta['model_version'],
        'scope':'whole_image_generation_only',
        'research_only':True,
        'source_attribution':{'status':'not_supported'},
        'provenance':{'status':'not_checked'},
        'forensic_observations':observations,
        'limitations':meta['limitations'],
        'processing_time_ms':round((perf_counter()-started)*1000,2),
    }

# BP_VISUAL_RESEARCH_ADAPTER_V1
# Deliberately preserve _model_bundle and existing five-feature function for regression,
# explanatory forensic observations, and immediate fallback if the visual worker is unavailable.
_baseline_detect_image = detect_image

def detect_image(image_bytes: bytes, *, content_already_validated: bool = False) -> dict:
    import json as _json
    import subprocess as _subprocess
    import hashlib as _hashlib
    from pathlib import Path as _Path
    if not content_already_validated:
        open_document_image(image_bytes)
    _manifest = MODEL_DIR / 'bp_visual_candidate_manifest.json'
    _weight = MODEL_DIR / 'bp_visual_low_quality.onnx'
    _worker = MODEL_DIR.parent / 'bp_visual_worker.py'
    if not (_manifest.is_file() and _weight.is_file() and _worker.is_file()):
        return _baseline_detect_image(image_bytes, content_already_validated=True)
    try:
        _meta = _json.loads(_manifest.read_text(encoding='utf-8'))
        if _meta['sha256'] != '88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17':
            raise ValueError('Unexpected visual model manifest checksum')
        _python = _Path(_meta['worker_python'])
        if not _python.is_file():raise RuntimeError('Isolated visual Python not available')
        _process = _subprocess.run([str(_python), str(_worker), str(_weight)],
             input=image_bytes, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
             timeout=40, check=False)
        if _process.returncode != 0:raise RuntimeError('Visual inference unavailable')
        _result = _json.loads(_process.stdout)
        _score = float(_result['score'])
        if not math.isfinite(_score) or not 0 <= _score <= 1:
            raise ValueError('Visual model returned invalid score')
        _low = float(_meta['not_ai_max']); _high = float(_meta['ai_min'])
        if not (0 <= _low < _high <= 1):raise ValueError('Invalid visual screening thresholds')
        _decision = ('likely_not_ai_generated' if _score <= _low else
                     'likely_ai_generated' if _score >= _high else 'inconclusive')
        # Preserve independently measured forensic observations, but do not let
        # unvalidated five-feature scores override the visual model's decision.
        _legacy = _baseline_detect_image(image_bytes, content_already_validated=True)
        _legacy.update({
            'status':'completed', 'decision':_decision,
            'ai_generated': (True if _decision == 'likely_ai_generated' else
                             False if _decision == 'likely_not_ai_generated' else None),
            'ai_generation_score':round(_score,4),
            'not_ai_generation_score':round(1-_score,4),
            'score_interpretation':'Research visual model calibrated score; not probability of provenance, document authenticity or identity',
            'thresholds':{'not_ai_max':_low,'ai_min':_high},
            'model_version':_meta['model_version'],
            'research_only':True,
            'limitations':list(_legacy.get('limitations',[]))+[
                'Independent full-resolution performance on this user\'s image sources not established',
                'CIFAKE local validation was previously explored and does not establish unseen-generator performance',
                'Neither low AI-generation score nor likely-not-AI label proves a photograph is real or genuine'],
        })
        return _legacy
    except Exception:
        # Failing closed is critical: do not silently replace a failed candidate
        # with a definite label from the old model.
        return {'status':'unavailable', 'decision':'inconclusive','ai_generated':None,
                'ai_generation_score':None,'not_ai_generation_score':None,
                'model_version':'visual_research_model_unavailable',
                'research_only':True,'scope':'whole_image_generation_only',
                'source_attribution':{'status':'not_supported'},
                'provenance':{'status':'not_checked'},
                'limitations':['Visual research detector unavailable; no generation conclusion can be drawn.']}
