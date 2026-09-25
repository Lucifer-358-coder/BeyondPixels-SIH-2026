"""Conservative single-image file metadata/provenance observations.

This module reports metadata that is already embedded in the uploaded file. It does
NOT authenticate the file, verify C2PA signatures, or infer forgery from missing or
present metadata.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any
from PIL import Image, ExifTags


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8", "replace")
        except Exception:
            return None
    value = str(value).strip()
    return value[:240] if value else None


def inspect_file_metadata(data: bytes) -> dict:
    """Return bounded, non-authenticating metadata observations for JPEG/PNG."""
    result = {
        "status": "not_assessed",
        "finding": "metadata_unavailable",
        "method": "embedded_file_metadata_v1",
        "format": None,
        "metadata_present": False,
        "software": None,
        "camera_make": None,
        "camera_model": None,
        "datetime": None,
        "c2pa_marker_candidate": False,
        "message": (
            "Embedded metadata was not available. Missing metadata is common after "
            "messaging, screenshots, exports, or privacy stripping and does not imply tampering."
        ),
    }
    try:
        with Image.open(BytesIO(data)) as image:
            fmt = (image.format or "").upper() or None
            result["format"] = fmt
            info = dict(image.info or {})
            exif_map = {}
            try:
                exif = image.getexif()
                if exif:
                    for key, value in exif.items():
                        name = ExifTags.TAGS.get(key, str(key))
                        exif_map[name] = value
            except Exception:
                exif_map = {}

            # Common EXIF and PNG textual metadata names.
            software = _text(exif_map.get("Software") or info.get("Software") or info.get("software"))
            make = _text(exif_map.get("Make") or info.get("Make") or info.get("make"))
            model = _text(exif_map.get("Model") or info.get("Model") or info.get("model"))
            dt = _text(
                exif_map.get("DateTimeOriginal") or exif_map.get("DateTime")
                or info.get("DateTimeOriginal") or info.get("DateTime") or info.get("date:create")
            )
            result.update({
                "software": software,
                "camera_make": make,
                "camera_model": model,
                "datetime": dt,
            })
            interesting = [software, make, model, dt]
            textual_keys = [k for k, v in info.items() if isinstance(v, (str, bytes)) and _text(v)]
            present = any(interesting) or bool(exif_map) or bool(textual_keys)
            result["metadata_present"] = present

            # Presence-only marker scan. This is intentionally NOT signature validation.
            lower = data.lower()
            result["c2pa_marker_candidate"] = (b"c2pa" in lower or b"jumb" in lower)

            result["status"] = "completed"
            if software:
                result["finding"] = "software_tag_present"
                result["message"] = (
                    "A software metadata tag is embedded in the file. Software tags can come from "
                    "legitimate capture, scanning, conversion, or editing workflows and are not a tampering verdict."
                )
            elif present:
                result["finding"] = "metadata_present"
                result["message"] = (
                    "Some embedded metadata is present. Metadata can be changed or removed and does not establish provenance or authenticity."
                )
            else:
                result["finding"] = "no_embedded_metadata"
                result["message"] = (
                    "No useful embedded metadata was found. This is common after screenshots, messaging, exports, or privacy stripping and is inconclusive."
                )
            if result["c2pa_marker_candidate"]:
                result["message"] += " A C2PA/JUMBF marker candidate was observed; this marker scan has NOT validated it. See the separate C2PA SDK result."
            return result
    except Exception:
        result["message"] = "File metadata could not be inspected; no provenance conclusion was produced."
        return result
