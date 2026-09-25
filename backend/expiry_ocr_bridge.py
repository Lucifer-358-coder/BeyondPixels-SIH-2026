"""Conservative adapter for the locked, experimental expiry-date OCR.

This does not establish document authenticity, validity, or tampering.
Original research scripts and MRZ validation are not modified.
"""
from __future__ import annotations

from datetime import date
import hashlib
import importlib
from pathlib import Path
import re
import sys

_EXPERIMENTS = Path(__file__).resolve().parent / "experiments"
_LOCKED_SCRIPTS = {
    "spatial_expiry_extractor_v01.py": "5a75f0ba7ad2aab9c7846c9b4d25cf05cee5165f611a27854506e9d0c699cc47",
    "spatial_expiry_extractor_v02.py": "94c418bf338def6d5c84d86b4a0bee385087d12ae122ab32f08b84c39e80eb79",
    "spatial_expiry_extractor_v03.py": "d45efb6574cca3fd368ad19188309b7d98ae38f9563975027f26ce1a46cc610c",
}
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def _run_locked_extractor(image):
    """Load only the exact reviewed research scripts from this backend."""
    for filename, digest in _LOCKED_SCRIPTS.items():
        path = _EXPERIMENTS / filename
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Locked expiry OCR scripts are missing or changed")

    experiments_path = str(_EXPERIMENTS)
    if experiments_path not in sys.path:
        sys.path.append(experiments_path)

    for module_name in (
        "spatial_expiry_extractor_v01",
        "spatial_expiry_extractor_v02",
        "spatial_expiry_extractor_v03",
    ):
        module = importlib.import_module(module_name)
        expected_path = (_EXPERIMENTS / f"{module_name}.py").resolve()
        if Path(module.__file__).resolve() != expected_path:
            raise RuntimeError("Expiry OCR module loaded from the wrong location")

    module = importlib.import_module("spatial_expiry_extractor_v03")
    return module.extract_expiry(image)


def integrate_expiry_ocr(image, original_fields):
    """Merge only a nonconflicting, explicitly labelled ISO expiry into OCR fields.

    Return (fields, metadata). An ambiguity/conflict suppresses the display
    expiry rather than silently choosing between two different observations.
    Missing or broken optional OCR retains preexisting fields.
    """
    fields = dict(original_fields)
    try:
        result = _run_locked_extractor(image)
        if not isinstance(result, dict):
            raise ValueError("Invalid expiry extraction response")
        status = result.get("status")
        expiry = result.get("expiry_date")
        method = result.get("method")
        if status not in ("extracted", "not_found", "ambiguous"):
            raise ValueError("Unknown expiry extraction status")
        if method is not None and not isinstance(method, str):
            raise ValueError("Invalid expiry extraction method")
        if status == "extracted":
            if not isinstance(expiry, str) or not _ISO_DATE.fullmatch(expiry):
                raise ValueError("Invalid expiry date representation")
            date.fromisoformat(expiry)
        elif expiry is not None:
            raise ValueError("Non-extracted result unexpectedly included a date")
    except Exception:
        # No raw document content, OCR text, or exception internals in API output.
        return fields, {"status": "unavailable", "method": None}

    if status == "ambiguous":
        fields.pop("expiry_date", None)
        return fields, {"status": "ambiguous", "method": method}

    if status == "not_found":
        # A prior explicit same-line OCR field is left unchanged, but is not
        # misrepresented as verified by the spatial experiment.
        return fields, {"status": "not_found", "method": method}

    prior = fields.get("expiry_date")
    if prior is not None and prior != expiry:
        # Different OCR observations, or an unrecognized date format: no guess.
        fields.pop("expiry_date", None)
        return fields, {"status": "conflict", "method": method}

    fields["expiry_date"] = expiry
    return fields, {"status": "extracted", "method": method}
