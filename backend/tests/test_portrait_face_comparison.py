"""Contract tests do not pretend to validate face recognition accuracy."""
import io
from unittest.mock import patch
from PIL import Image
import portrait_face_comparison as comp


def picture():
    return Image.new("RGB", (200, 200), "white")


def test_no_photo_always_abstains():
    r = comp.compare_document_face(picture(), None)
    assert r["status"] == "not_assessed"
    assert r["cosine_similarity"] is None
    assert r["identity_verified"] is False


def test_missing_weights_never_claims_match():
    with patch.object(comp, "DETECTOR", type(comp.DETECTOR)("/missing/yunet.onnx")), \
         patch.object(comp, "RECOGNIZER", type(comp.RECOGNIZER)("/missing/sface.onnx")):
        r = comp.compare_document_face(picture(), picture())
    assert r["status"] == "unavailable"
    assert r["identity_verified"] is False


def test_multiple_or_missing_faces_abstains():
    with patch.object(comp, "DETECTOR") as d, patch.object(comp, "RECOGNIZER") as m, \
         patch.object(comp, "_detect_one", side_effect=[(None,None,2),(None,None,1)]):
        d.is_file.return_value = True
        m.is_file.return_value = True
        with patch.object(comp.cv2, "FaceDetectorYN_create", return_value=object()):
            r = comp.compare_document_face(picture(), picture())
    assert r["status"] == "not_assessed"
    assert r["cosine_similarity"] is None


def test_output_is_nonidentifying_and_no_image_data():
    r=comp._out("completed","similarity_observed","research",1,1,0.7)
    assert r["identity_verified"] is False
    assert r["portrait_replacement_detected"] is None
    assert "embedding" not in r and "image" not in r
