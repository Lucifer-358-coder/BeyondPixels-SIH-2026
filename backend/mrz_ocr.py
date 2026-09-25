"""Conservative MRZ OCR for experimental TD3 passport images.

Uses the photographed glyphs to distinguish '<' filler characters from
letters when whole-line Tesseract OCR produces 44 characters but garbles
fillers, or returns 40/45 characters. It does NOT insert characters based on
checksums, alter check digits, or pick a candidate for checksum success.
This is a research prototype, not an identity verification system.
"""
from __future__ import annotations

import re

import numpy as np
from PIL import Image, ImageOps

_MRZ_CHARS = re.compile(r"[A-Z0-9<]{44}\Z")
_RUN_CHARS = re.compile(r"[A-Z0-9<]+\Z")
_MRZ_CONFIG = (
    "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789< "
    "-c load_system_dawg=0 -c load_freq_dawg=0"
)


def _text_bands(image: Image.Image) -> list[tuple[int, int, int, int]]:
    """Find broad, separate horizontal dark-text bands in lower image area."""
    gray = np.asarray(ImageOps.grayscale(image))
    height, width = gray.shape
    if width < 350 or height < 160:
        return []
    mask = gray < 165
    start = int(height * 0.35)
    active = (mask.sum(axis=1) >= max(15, int(width * 0.015)))
    active[:start] = False
    boundary = np.flatnonzero(np.diff(np.r_[False, active, False]))
    candidates = []
    for top, bottom in zip(boundary[::2], boundary[1::2]):
        if bottom - top < 8:
            continue
        ys, xs = np.where(mask[top:bottom])
        if xs.size == 0:
            continue
        left, right = int(xs.min()), int(xs.max()) + 1
        if right - left < width * 0.4:
            continue
        pad_x = max(8, round(width * 0.005))
        pad_y = max(6, round(height * 0.015))
        candidates.append((max(0, left - pad_x), max(0, int(top) - pad_y),
                           min(width, right + pad_x), min(height, int(bottom) + pad_y)))
    return candidates


def _ocr(crop: Image.Image, psm: int, scale: int) -> str:
    import pytesseract

    gray = ImageOps.autocontrast(crop.convert("L"))
    sample = (gray.resize((gray.width * scale, gray.height * scale),
                          Image.Resampling.BICUBIC) if scale != 1 else gray)
    return "".join(pytesseract.image_to_string(
        sample, config=f"--psm {psm} {_MRZ_CONFIG}", timeout=8
    ).upper().split())


def _read_line(crop: Image.Image, first_line: bool) -> str | None:
    """Conventional conservative whole-line OCR fallback."""
    for psm, scale in ((13, 2), (7, 1), (13, 1), (7, 2)):
        candidate = _ocr(crop, psm, scale)
        if _MRZ_CHARS.fullmatch(candidate) and (not first_line or candidate.startswith("P<")):
            return candidate
    return None


def _glyphs(crop: Image.Image):
    """Return the 44 photographed, visually separated character regions.

    Projection segmentation works on the supplied *synthetic monospaced*
    examples. If characters touch, scans are noisy, or spacing is irregular,
    give up rather than assume there are 44 characters.
    """
    gray = np.asarray(ImageOps.grayscale(crop))
    binary = gray < 165
    occupied = np.flatnonzero(binary.any(axis=0))
    if len(occupied) == 0:
        return None
    spans = []
    start = last = int(occupied[0])
    for col in occupied[1:]:
        col = int(col)
        if col > last + 1:
            spans.append((start, last))
            start = col
        last = col
    spans.append((start, last))
    if len(spans) != 44:
        return None
    # Require approximately regular monospaced centers. Avoid interpreting
    # arbitrary horizontal marks as individual passport glyphs.
    centers = np.array([(left + right) / 2 for left, right in spans])
    pitch = np.diff(centers)
    if pitch.min() <= 0 or np.max(np.abs(pitch - np.median(pitch))) > 0.28 * np.median(pitch):
        return None
    masks = []
    for left, right in spans:
        rows = np.flatnonzero(binary[:, left:right + 1].any(axis=1))
        if not len(rows) or right - left < 1:
            return None
        symbol = (binary[rows[0]:rows[-1] + 1, left:right + 1]
                  .astype(np.uint8) * 255)
        # Nearest neighbor retains the shape of the observed pixels; it never
        # renders/replaces a character from a synthetic font.
        from PIL import Image as PILImage
        normalized = PILImage.fromarray(symbol).resize((24, 32), PILImage.Resampling.NEAREST)
        masks.append(np.asarray(normalized) > 0)
    return spans, masks


def _read_segmented(bands: list[Image.Image]) -> str | None:
    """Recover visually isolated glyphs, never using MRZ checksum feedback.

    The first TD3 glyphs must read P<; use the photographed '<' glyph as
    a reference for other identical glyph SHAPES (not their expected position).
    OCR each remaining contiguous run without adjacent filler interference.
    Reject if any OCR run has the wrong observed character count.
    """
    segmented = [_glyphs(band) for band in bands]
    if any(result is None for result in segmented):
        return None
    # Verify the P< anchor from actual image text before trusting its glyph.
    if not any(_ocr(bands[0], psm, scale).startswith("P<")
               for psm, scale in ((7, 1), (13, 2))):
        return None
    template = segmented[0][1][1]
    recovered = []
    filler_count = 0
    for band, (spans, masks) in zip(bands, segmented):
        filler = [float(np.mean(mask != template)) <= 0.10 for mask in masks]
        filler_count += sum(filler)
        characters = ["<" if is_filler else "?" for is_filler in filler]
        index = 0
        while index < 44:
            if filler[index]:
                index += 1
                continue
            end = index
            while end + 1 < 44 and not filler[end + 1]:
                end += 1
            # Crop at halfway points to neighboring glyphs; do not inadvertently
            # bring adjacent '<' into the OCR of an alphabetic/numeric run.
            left = (int((spans[index - 1][1] + spans[index][0]) // 2 + 1)
                    if index else max(0, spans[index][0] - 3))
            right = (int((spans[end][1] + spans[end + 1][0]) // 2 + 1)
                     if end < 43 else min(band.width, spans[end][1] + 4))
            block = band.crop((left, 0, right, band.height))
            text = None
            for psm, scale in ((7, 2), (13, 2), (7, 1), (13, 1)):
                candidate = _ocr(block, psm, scale)
                if len(candidate) == end - index + 1 and _RUN_CHARS.fullmatch(candidate):
                    text = candidate
                    break
            if text is None:
                return None
            characters[index:end + 1] = text
            index = end + 1
        line = "".join(characters)
        if not _MRZ_CHARS.fullmatch(line):
            return None
        recovered.append(line)
    # Require multiple actual filler-shaped symbols, not one unreliable anchor.
    if filler_count < 3 or not recovered[0].startswith("P<"):
        return None
    return "\n".join(recovered)


def extract_td3_mrz(image: Image.Image) -> dict:
    """Return visually recovered literal 44-character lines or uncertainty.

    No edits made to check digits, no predictions based on checksums; an OCR
    mistake can still produce a checksum mismatch requiring manual review.
    """
    try:
        locations = _text_bands(image)
        if len(locations) < 2:
            return {"status": "not_detected", "text": ""}
        bands = [image.crop(rect) for rect in locations[-2:]]
        # Prefer character-by-character VISUAL segmentation when possible;
        # full-line Tesseract can manufacture a 44-character string of K's.
        segmented = _read_segmented(bands)
        if segmented is not None:
            return {"status": "detected", "text": segmented}
        first = _read_line(bands[0], first_line=True)
        second = _read_line(bands[1], first_line=False)
        if first is None or second is None:
            return {"status": "not_detected", "text": ""}
        return {"status": "detected", "text": first + "\n" + second}
    except (ImportError, OSError):
        return {"status": "unavailable", "text": ""}
    except Exception:
        return {"status": "not_detected", "text": ""}
