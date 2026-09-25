from pathlib import Path
from datetime import date
import re
import hashlib

import pytesseract
from pytesseract import Output

from media import open_document_image

ROOT = Path("data/research_single_image_documents_v01")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def extract_expiry(image):
    """Experimental spatial OCR; receives image pixels only."""
    data = pytesseract.image_to_data(
        image, config="--psm 6", output_type=Output.DICT
    )

    words = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        if not text:
            continue
        x = int(data["left"][i])
        y = int(data["top"][i])
        words.append({
            "text": text,
            "x1": x,
            "y1": y,
            "x2": x + int(data["width"][i]),
            "y2": y + int(data["height"][i]),
        })

    candidates = []

    for expiry in words:
        if re.sub(r"[^A-Za-z]", "", expiry["text"]).upper() != "EXPIRY":
            continue

        # Require a nearby DATE word on approximately the same row.
        matching_labels = [
            word for word in words
            if re.sub(r"[^A-Za-z]", "", word["text"]).upper() == "DATE"
            and 0 <= word["x1"] - expiry["x2"] <= 35
            and abs(word["y1"] - expiry["y1"]) <= 15
        ]
        if not matching_labels:
            continue

        for word in words:
            if not DATE_PATTERN.fullmatch(word["text"]):
                continue

            try:
                date.fromisoformat(word["text"])
            except ValueError:
                continue

            vertical_gap = word["y1"] - expiry["y2"]
            horizontal_offset = abs(word["x1"] - expiry["x1"])

            if 0 <= vertical_gap <= 100 and horizontal_offset <= 80:
                candidates.append((
                    vertical_gap + horizontal_offset,
                    word["text"],
                ))

    # Do not silently choose between competing OCR interpretations.
    distinct_dates = {value for _, value in candidates}
    if len(distinct_dates) == 1:
        return {"status": "extracted", "expiry_date": distinct_dates.pop()}
    if len(distinct_dates) > 1:
        return {"status": "ambiguous", "expiry_date": None}
    return {"status": "not_found", "expiry_date": None}


def main():
    print("=== DEVELOPMENT-ONLY SPATIAL EXPIRY CHECK ===")
    matched = 0
    total = 0

    for number in range(1, 13):
        family = f"fictional_document_{number:02d}"
        layout = "A" if number <= 4 else "B" if number <= 8 else "C"

        cases = [
            (
                "reference",
                ROOT / "development_references" / f"{family}_reference.png",
                f"203{number % 10}-08-21",
            ),
            (
                "expiry_edit",
                ROOT / "development_variants_v01" / family / "edit_expiry.png",
                f"204{number % 10}-11-25",
            ),
        ]

        for kind, path, expected in cases:
            total += 1
            result = extract_expiry(open_document_image(path.read_bytes()))
            actual = result["expiry_date"]
            passed = result["status"] == "extracted" and actual == expected
            matched += int(passed)

            print(
                f"{family} layout={layout} {kind}: "
                f"status={result['status']} "
                f"expected={expected} actual={actual} "
                f"match={passed}"
            )

    print(f"\nEXACT EXPIRY MATCHES: {matched}/{total}")
    print("Development images only; evaluation images not accessed.")
    print("No production app, models, or UI changed.")


if __name__ == "__main__":
    main()
