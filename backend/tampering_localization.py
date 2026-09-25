"""Conservative *paired-reference* pixel-change localization for fictional documents.

This is NOT standalone forgery/portrait replacement detection. It compares two
same-size PNG pixel arrays against an operator-supplied, independently trusted
reference, and abstains when a meaningful registration is not established.
No images, crops, field values, or overlays are stored or returned as bytes.
"""
from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
from PIL import Image

MAX_PAIR_PIXELS = 4_000_000
MAX_CHANGED_FRACTION = 0.025


def _unassessed(reason: str, message: str) -> dict:
    return {
        "status": "not_assessed", "method": "png_reference_pixel_difference_v1",
        "finding": "inconclusive", "reason": reason, "regions_detected": 0,
        "top_regions": [], "overlay_available": False,
        "message": message,
        "limitation": "No standalone forgery, editing history, or portrait-replacement detection.",
    }


def localize_document_pixel_differences(image: Image.Image, image_bytes: bytes,
                                        reference: Image.Image | None,
                                        reference_bytes: bytes | None) -> dict:
    """Return normalized candidate boxes only for an aligned PNG reference pair.

    Changed pixels are not evidence of unauthorized modification: resizing,
    printing, rescanning, layout edits, and a wrong reference all cause changes.
    """
    if reference is None or reference_bytes is None:
        return _unassessed("reference_required", "Choose an authorized PNG reference of the same fictional document to compare pixels.")
    try:
        with Image.open(BytesIO(image_bytes)) as current_probe, Image.open(BytesIO(reference_bytes)) as reference_probe:
            if current_probe.format != "PNG" or reference_probe.format != "PNG":
                return _unassessed("png_pair_required", "Paired localization requires two lossless PNG files; JPEG compression creates misleading differences.")
    except (OSError, ValueError):
        return _unassessed("unreadable_pair", "Could not read the document/reference encoding.")
    if image.size != reference.size:
        return _unassessed("dimensions_differ", "Document and reference must have identical pixel dimensions and alignment.")
    width, height = image.size
    if width * height > MAX_PAIR_PIXELS:
        return _unassessed("pair_too_large", "Paired comparison is limited to four megapixels to bound memory usage.")

    left = np.asarray(image.convert("RGB"), dtype=np.uint8)
    right = np.asarray(reference.convert("RGB"), dtype=np.uint8)
    delta = cv2.absdiff(left, right)
    # Large differences in at least one channel; lossless pairs only.
    changed = np.uint8(np.max(delta, axis=2) > 24) * 255
    changed_count = int(np.count_nonzero(changed))
    fraction = changed_count / (width * height)
    if fraction > MAX_CHANGED_FRACTION:
        return _unassessed("alignment_or_reference_uncertain",
                           "Too many pixels differ to localize reliably; check reference, alignment, or acquisition conditions.")
    if changed_count == 0:
        return {
            "status": "completed", "method": "png_reference_pixel_difference_v1",
            "finding": "no_detected_pixel_difference", "reason": "identical_decoded_pixels",
            "regions_detected": 0, "top_regions": [], "overlay_available": False,
            "message": "Decoded pixels match the supplied reference. This does not establish authenticity.",
            "limitation": "An identical image can still be altered relative to an unknown original.",
        }

    # Bridge strokes of edited glyphs so each proposed region is reviewable.
    joined = cv2.morphologyEx(changed, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    joined = cv2.dilate(joined, cv2.getStructuringElement(cv2.MORPH_RECT, (13, 7)))
    count, _, stats, _ = cv2.connectedComponentsWithStats(joined, 8)
    regions = []
    for x, y, box_width, box_height, area in stats[1:count]:
        x, y, box_width, box_height, area = map(int, (x, y, box_width, box_height, area))
        if area < 65 or box_width < 4 or box_height < 4:
            continue
        actual_changed = int(np.count_nonzero(changed[y:y + box_height, x:x + box_width]))
        if actual_changed < 28:
            continue
        # Use fractions so Flutter can draw boxes on its own original image.
        regions.append({
            "x": round(x / width, 6), "y": round(y / height, 6),
            "width": round(box_width / width, 6), "height": round(box_height / height, 6),
            "changed_pixels": actual_changed,
        })
    regions.sort(key=lambda item: item["changed_pixels"], reverse=True)
    if not regions:
        return _unassessed("unlocalized_small_differences",
                           "A small number of pixels differ, but no sufficiently coherent region was found.")
    if len(regions) > 30:
        return _unassessed("too_many_regions", "Too many separate differences to present reliable regions; inspect image alignment.")
    return {
        "status": "completed", "method": "png_reference_pixel_difference_v1",
        "finding": "localized_pixel_differences", "reason": "aligned_reference_pair",
        "regions_detected": len(regions), "top_regions": regions[:12],
        "overlay_available": True, "image_width": width, "image_height": height,
        "message": "Highlighted locations differ from the operator-supplied reference; verify the reference and review changes manually.",
        "limitation": "Differences do not prove tampering, a forged document, or portrait replacement. Not a standalone detector.",
    }
