"""Experimental local face-manipulation analysis. No identity verification.

Checkpoint credit: Xicor9/efficientnet-b0-ffpp-c23, FaceForensics++ C23.
https://huggingface.co/Xicor9/efficientnet-b0-ffpp-c23
The model author specifies academic/research use only, not real-world forensics.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
WEIGHTS = ROOT / "models" / "deepfake_ffpp_c23.pth"
WORKER = ROOT / "deepfake_worker.py"
VENV_PYTHON = ROOT / ".venv_deepfake" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MODEL_NAME = "Xicor9/efficientnet-b0-ffpp-c23 (research checkpoint)"
EXPECTED_SHA256 = "2a7963b787ece2594a79160f20e53d6bc621f6bfe34ee21d139efa81bcb70c84"


def deepfake_ready() -> bool:
    return (WEIGHTS.is_file() and 10_000_000 < WEIGHTS.stat().st_size < 30_000_000
            and VENV_PYTHON.is_file() and WORKER.is_file()
            and Path(cv2.data.haarcascades, "haarcascade_frontalface_default.xml").is_file())


def _unavailable(message: str) -> dict:
    return {"status": "unavailable", "decision": None, "face_count": None,
            "faces_analyzed": 0, "faces": [], "model": MODEL_NAME, "message": message}


def analyze_deepfake(image_bytes: bytes) -> dict:
    """Returns separate per-face model observations or an explicit non-verdict."""
    if not deepfake_ready():
        return _unavailable("Local face-manipulation model is not installed or ready.")
    try:
        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            return {**_unavailable("Cannot decode this image."), "status": "not_assessed", "face_count": 0}
        detector = cv2.CascadeClassifier(
            str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"))
        if detector.empty():
            return _unavailable("Frontal face detector unavailable.")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # BP_JUDGE_DEMO_YUNET_FALLBACK_V1
        # Face localization only. Never infer deepfake status from a face box.
        boxes = []
        yunet_model = ROOT / "models" / "face_detection_yunet_2023mar.onnx"
        if yunet_model.is_file() and hasattr(cv2, "FaceDetectorYN"):
            try:
                detector_yn = cv2.FaceDetectorYN.create(
                    model=str(yunet_model), config="", input_size=(320, 320),
                    score_threshold=0.6, nms_threshold=0.3, top_k=100)
                resized = cv2.resize(image, (320, 320), interpolation=cv2.INTER_AREA)
                _, found = detector_yn.detect(resized)
                if found is not None:
                    orig_h, orig_w = image.shape[:2]
                    for face in found:
                        left = max(0, min(orig_w - 1, round(float(face[0]) * orig_w / 320)))
                        top = max(0, min(orig_h - 1, round(float(face[1]) * orig_h / 320)))
                        right = max(left + 1, min(orig_w, round(float(face[0] + face[2]) * orig_w / 320)))
                        bottom = max(top + 1, min(orig_h, round(float(face[1] + face[3]) * orig_h / 320)))
                        if right - left >= 20 and bottom - top >= 20:
                            boxes.append((left, top, right - left, bottom - top))
            except (cv2.error, AttributeError, ValueError):
                boxes = []
        if not boxes:
            boxes = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        boxes = sorted((tuple(map(int, box)) for box in boxes),
                       key=lambda b: b[2] * b[3], reverse=True)
        if not boxes:
            return {"status": "not_assessed", "decision": None, "face_count": 0,
                    "faces_analyzed": 0, "faces": [], "model": MODEL_NAME,
                    "message": "No frontal face detected; no deepfake verdict."}
        height, width = image.shape[:2]
        with tempfile.TemporaryDirectory(prefix="bp_face_") as tmp:
            paths = []
            for i, (x, y, w, h) in enumerate(boxes[:3]):
                pad = int(max(w, h) * 0.15)
                x0, y0 = max(0, x - pad), max(0, y - pad)
                x1, y1 = min(width, x + w + pad), min(height, y + h + pad)
                crop = image[y0:y1, x0:x1]
                if crop.size == 0:
                    return _unavailable("Could not prepare a face crop.")
                path = Path(tmp) / f"face_{i}.png"
                if not cv2.imwrite(str(path), crop):
                    return _unavailable("Could not prepare a face crop.")
                paths.append(str(path))
            completed = subprocess.run(
                [str(VENV_PYTHON), "-I", str(WORKER), "--model", str(WEIGHTS),
                 "--images", *paths], capture_output=True, text=True,
                timeout=45, check=False, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"},
            )
            if completed.returncode != 0:
                return _unavailable("Local deepfake inference failed; no verdict.")
            payload = json.loads(completed.stdout)
            scores = payload.get("scores")
            if not isinstance(scores, list) or len(scores) != len(paths):
                return _unavailable("Invalid model output; no verdict.")
            faces = []
            for (x, y, w, h), score in zip(boxes[:3], scores):
                if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score) or not 0 <= score <= 1:
                    return _unavailable("Invalid model score; no verdict.")
                # UI bands are illustrative, NOT validated decision thresholds.
                decision = ("possible_manipulation" if score >= 0.65 else
                            "no_strong_indicators" if score <= 0.35 else "inconclusive")
                faces.append({"box": [x, y, w, h], "fake_score": round(float(score), 4),
                              "decision": decision})
            return {"status": "completed" if len(boxes) <= 3 else "partial",
                    "decision": "possible_manipulation" if any(f["decision"] == "possible_manipulation" for f in faces) else
                                "inconclusive" if any(f["decision"] == "inconclusive" for f in faces) else "no_strong_indicators",
                    "face_count": len(boxes), "faces_analyzed": len(faces), "faces": faces,
                    "model": MODEL_NAME,
                    "message": "Experimental FaceForensics++ C23 model. Face crops may differ from training; scores and display bands are uncalibrated and do not establish authenticity or identity."}
    except (OSError, ValueError, RuntimeError, cv2.error, subprocess.TimeoutExpired, json.JSONDecodeError):
        return _unavailable("Face-manipulation analysis could not complete; no verdict.")
