"""Experimental spatial expiry OCR with a focused-label fallback.

Image pixels are the only inference input. No reference, manifest,
filename, ground-truth label, or document-authenticity claim is used.
"""
from datetime import date
import re

import pytesseract
from pytesseract import Output

from spatial_expiry_extractor_v01 import extract_expiry as extract_v01

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def extract_expiry(image):
    first = extract_v01(image)

    # Preserve a successful or ambiguous v01 result.
    if first["status"] != "not_found":
        return {**first, "method": "spatial_v01"}

    data = pytesseract.image_to_data(
        image, config="--psm 6", output_type=Output.DICT
    )

    labelled_dates = set()

    for i, raw in enumerate(data["text"]):
        candidate = raw.strip()

        if not ISO_DATE.fullmatch(candidate):
            continue

        try:
            date.fromisoformat(candidate)
        except ValueError:
            continue

        x = int(data["left"][i])
        y = int(data["top"][i])

        # Search above each readable date for an explicit expiry label.
        box = (
            max(0, x - 10),
            max(0, y - 45),
            min(image.width, x + 230),
            max(0, y - 4),
        )

        if box[2] <= box[0] or box[3] <= box[1]:
            continue

        crop = image.crop(box)
        label = pytesseract.image_to_string(
            crop, config="--psm 7"
        )

        normalized = re.sub(r"\s+", " ", label).strip()
        normalized = normalized.strip(" :;.,").upper()

        # Do not accept DATE alone, DOB, or a garbled approximation.
        if normalized == "EXPIRY DATE":
            labelled_dates.add(candidate)

    if len(labelled_dates) == 1:
        return {
            "status": "extracted",
            "expiry_date": labelled_dates.pop(),
            "method": "focused_label_fallback",
        }

    if len(labelled_dates) > 1:
        return {
            "status": "ambiguous",
            "expiry_date": None,
            "method": "focused_label_fallback",
        }

    return {
        "status": "not_found",
        "expiry_date": None,
        "method": "focused_label_fallback",
    }
