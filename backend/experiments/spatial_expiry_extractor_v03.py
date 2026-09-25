"""Post-evaluation experimental expiry OCR v03.

Reads one image only. Does not establish tampering or authenticity.
"""
from datetime import date
import re

import pytesseract
from pytesseract import Output

from spatial_expiry_extractor_v02 import extract_expiry as extract_v02

DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def extract_expiry(image):
    first = extract_v02(image)
    if first["status"] != "not_found":
        return first

    data = pytesseract.image_to_data(
        image, config="--psm 6", output_type=Output.DICT
    )

    words = []
    for i, raw in enumerate(data["text"]):
        word = re.sub(r"[^A-Za-z]", "", raw).upper()
        if not word:
            continue

        x = int(data["left"][i])
        y = int(data["top"][i])

        words.append({
            "text": word,
            "x1": x,
            "y1": y,
            "x2": x + int(data["width"][i]),
            "y2": y + int(data["height"][i]),
        })

    found_dates = set()

    for word in words:
        if word["text"] != "EXPIRY":
            continue

        has_date_label = any(
            other["text"] == "DATE"
            and 0 <= other["x1"] - word["x2"] <= 35
            and abs(other["y1"] - word["y1"]) <= 15
            for other in words
        )

        if not has_date_label:
            continue

        # Search below the recognized label, without using
        # a reference image, filename, or template coordinates.
        box = (
            max(0, word["x1"] - 10),
            min(image.height, word["y2"] + 2),
            min(image.width, word["x1"] + 240),
            min(image.height, word["y2"] + 80),
        )

        if box[2] <= box[0] or box[3] <= box[1]:
            continue

        crop = image.crop(box)

        for psm in (7, 6):
            text = pytesseract.image_to_string(
                crop, config=f"--psm {psm}"
            )

            for candidate in DATE_RE.findall(text):
                try:
                    date.fromisoformat(candidate)
                except ValueError:
                    continue
                found_dates.add(candidate)

    if len(found_dates) == 1:
        return {
            "status": "extracted",
            "expiry_date": found_dates.pop(),
            "method": "label_anchored_crop_v03",
        }

    if len(found_dates) > 1:
        return {
            "status": "ambiguous",
            "expiry_date": None,
            "method": "label_anchored_crop_v03",
        }

    return {
        "status": "not_found",
        "expiry_date": None,
        "method": "label_anchored_crop_v03",
    }
