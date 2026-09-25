"""Optional OCR and STAI integration, with explicit unknown statuses."""
from __future__ import annotations

import os
from io import BytesIO


def extract_text(image) -> dict:
    try:
        import pytesseract
        from pytesseract import TesseractNotFoundError
        text = pytesseract.image_to_string(image, config="--psm 6", timeout=15)
        return {"status": "completed", "text": text}
    except (ImportError, OSError, TesseractNotFoundError) as exc:
        return {"status": "unavailable", "text": "", "message": type(exc).__name__}
    except Exception:
        # Avoid leaking raw image/PII or OCR internals to the client.
        return {"status": "error", "text": "", "message": "OCR processing failed"}


def inspect_stai(image_bytes: bytes, mime: str) -> dict:
    endpoint = os.environ.get("STAI_ANALYZE_URL", "").strip()
    if not endpoint:
        return {
            "status": "not_configured", "ai_generated": None,
            "reported_confidence": None, "model": "STAI", "source": "not_supported",
        }
    import requests
    try:
        response = requests.post(
            endpoint,
            files={"image": ("screening.jpg" if mime == "image/jpeg" else "screening.png", image_bytes, mime)},
            timeout=(3, 25),
        )
        response.raise_for_status()
        data = response.json()
        ai = data.get("is_ai")
        confidence = data.get("confidence")
        if type(ai) is not bool or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError("Invalid STAI response")
        return {
            "status": "completed", "ai_generated": ai,
            "reported_confidence": round(float(confidence), 4),
            "model": "STAI", "source": "not_supported",
            "note": "This image-level classifier is not a passport forgery detector; confidence is not a calibrated fraud probability.",
        }
    except (requests.RequestException, ValueError):
        return {
            "status": "unavailable", "ai_generated": None,
            "reported_confidence": None, "model": "STAI", "source": "not_supported",
        }
