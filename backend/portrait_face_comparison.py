"""Opt-in document-portrait to consented face-photo similarity observation.

Research-only: comparison of two face embeddings is NOT proof of identity,
portrait replacement, or document authenticity. No embeddings or photos stored.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

METHOD = "opencv_yunet_sface_cosine_research_v1"
MODEL_DIR = Path(__file__).resolve().parent / "models" / "face_similarity"
DETECTOR = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER = MODEL_DIR / "face_recognition_sface_2021dec.onnx"
# OpenCV Zoo's LFW-oriented example threshold is not calibrated for our document images.
EXAMPLE_COSINE_THRESHOLD = 0.363


def _out(status: str, finding: str, message: str, doc_faces=None, photo_faces=None,
         similarity=None) -> dict:
    return {
        "status": status, "finding": finding, "method": METHOD,
        "document_face_count": doc_faces,
        "photo_face_count": photo_faces,
        "cosine_similarity": similarity,
        "reference_threshold_observation": (
            None if similarity is None else
            "above_example_threshold" if similarity >= EXAMPLE_COSINE_THRESHOLD
            else "below_example_threshold"
        ),
        "identity_verified": False,
        "portrait_replacement_detected": None,
        "message": message,
    }


def _detect_one(detector, image: Image.Image):
    # Work is bounded; each image already passed open_document_image size limits.
    rgb = np.asarray(image.convert("RGB"))
    h, w = rgb.shape[:2]
    scale = min(1.0, 900.0 / max(h, w))
    if scale < 1.0:
        rgb = cv2.resize(rgb, (max(1, round(w * scale)), max(1, round(h * scale))),
                         interpolation=cv2.INTER_AREA)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return bgr, None, 0
    if len(faces) != 1:
        return bgr, None, len(faces)
    face = faces[0]
    if not np.isfinite(face).all() or face[2] < 35 or face[3] < 35:
        return bgr, None, 0
    return bgr, face, 1


def compare_document_face(document: Image.Image, comparison_photo: Image.Image | None) -> dict:
    """Return conservative similarity observations, only on explicit opt-in."""
    if comparison_photo is None:
        return _out("not_assessed", "no_comparison_photo",
                    "No optional face photo supplied. Only document portrait visibility was checked.")
    if not DETECTOR.is_file() or not RECOGNIZER.is_file():
        return _out("unavailable", "model_not_installed",
                    "Local face-comparison models are unavailable. No comparison performed.")
    try:
        if not hasattr(cv2, "FaceDetectorYN_create") or not hasattr(cv2, "FaceRecognizerSF_create"):
            return _out("unavailable", "opencv_unsupported", "OpenCV face model support unavailable.")
        detector = cv2.FaceDetectorYN_create(str(DETECTOR), "", (320, 320),
                                             score_threshold=0.85, nms_threshold=0.3,
                                             top_k=5000)
        doc_bgr, doc_face, doc_count = _detect_one(detector, document)
        photo_bgr, photo_face, photo_count = _detect_one(detector, comparison_photo)
        if doc_count != 1 or photo_count != 1:
            return _out("not_assessed", "face_count_not_one",
                        "Exactly one usable face is required in each image; no identity conclusion.",
                        doc_count, photo_count)
        recognizer = cv2.FaceRecognizerSF_create(str(RECOGNIZER), "")
        doc_aligned = recognizer.alignCrop(doc_bgr, doc_face)
        photo_aligned = recognizer.alignCrop(photo_bgr, photo_face)
        doc_features = recognizer.feature(doc_aligned)
        photo_features = recognizer.feature(photo_aligned)
        score = float(recognizer.match(doc_features, photo_features,
                                       cv2.FaceRecognizerSF_FR_COSINE))
        if not math.isfinite(score) or score < -1.0001 or score > 1.0001:
            return _out("unavailable", "invalid_similarity", "Model did not return a valid similarity.", 1, 1)
        return _out("completed", "similarity_observed",
                    "Uncalibrated facial similarity only. The OpenCV Zoo example threshold "
                    "has NOT been validated on identity-document portraits. "
                    "This result cannot verify identity or determine portrait replacement.",
                    1, 1, round(max(-1.0, min(1.0, score)), 5))
    except (cv2.error, ValueError, TypeError, OverflowError, MemoryError):
        return _out("unavailable", "inference_error",
                    "Face comparison could not complete; no identity conclusion.")
