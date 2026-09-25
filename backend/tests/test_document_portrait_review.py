"""YuNet portrait-visibility contract tests; never identity or forgery."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
import document_portrait_review as mod

class FakeDetector:
    def __init__(self, faces): self.faces=faces
    def setInputSize(self, _): pass
    def detect(self, _): return None, self.faces

def image(): return Image.new('RGB',(600,400),'white')

def _model_patch(tmp_path):
    p=tmp_path/'yunet.onnx'; p.write_bytes(b'x'); return patch.object(mod,'DETECTOR',p)

def test_no_face_not_assessed(tmp_path):
    with _model_patch(tmp_path), patch.object(mod.cv2,'FaceDetectorYN_create',return_value=FakeDetector(None)):
        r=mod.review_document_portrait(image())
    assert r['status']=='not_assessed' and r['faces_detected']==0

def test_one_high_confidence_face(tmp_path):
    face=np.array([[100,75,110,110,0,0,0,0,0,0,0,0,0,0,0.97]],dtype=np.float32)
    with _model_patch(tmp_path), patch.object(mod.cv2,'FaceDetectorYN_create',return_value=FakeDetector(face)):
        r=mod.review_document_portrait(image())
    assert r['status']=='completed' and r['faces_detected']==1 and r['overlay_available'] is True
    assert r['portrait_replacement_detected'] is None

def test_low_confidence_or_tiny_candidate_rejected(tmp_path):
    face=np.array([[10,10,20,20,0,0,0,0,0,0,0,0,0,0,0.99]],dtype=np.float32)
    with _model_patch(tmp_path), patch.object(mod.cv2,'FaceDetectorYN_create',return_value=FakeDetector(face)):
        r=mod.review_document_portrait(image())
    assert r['status']=='not_assessed' and r['faces_detected']==0

def test_missing_model_unavailable(tmp_path):
    with patch.object(mod,'DETECTOR',tmp_path/'missing.onnx'):
        r=mod.review_document_portrait(image())
    assert r['status']=='unavailable' and r['identity_verified'] is False
