"""Opt-in, request-scoped visual-duplicate candidates against operator-supplied images.

No persistent gallery, identity linking, remote search, face biometrics, or claim
that an image/document is authentic. Hashes and original images stay in memory.
"""
from __future__ import annotations

from hashlib import sha256
from PIL import Image, ImageStat

MAX_REFERENCES = 4


def _hash(image: Image.Image) -> int:
    # dHash: orientation- and crop-sensitive; a *candidate* signal only.
    tiny = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(tiny.get_flattened_data() if hasattr(tiny, "get_flattened_data") else tiny.getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            value = (value << 1) | (pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return value


def review_authorized_references(image: Image.Image, source: bytes,
                                 references: list[tuple[Image.Image, bytes]]) -> dict:
    if not references:
        return {'status': 'not_assessed', 'finding': 'reference_images_not_provided',
                'references_compared': 0, 'candidates': [],
                'message': 'Add authorized reference images to opt into in-session comparison.'}
    if len(references) > MAX_REFERENCES:
        raise ValueError('Too many authorized reference images')
    digest = sha256(source).digest()
    main_hash = _hash(image)
    main_gray = ImageStat.Stat(image.convert('L').resize((64, 64))).stddev[0]
    count = main_hash.bit_count()
    candidates = []
    for idx, (other, content) in enumerate(references, 1):
        if sha256(content).digest() == digest:
            candidates.append({'reference_index': idx, 'observation': 'exact_file_duplicate',
                               'distance_bits': 0})
            continue
        ratio = image.width / image.height / (other.width / other.height)
        if not (0.75 <= ratio <= 1.33):
            continue
        other_hash = _hash(other)
        other_std = ImageStat.Stat(other.convert('L').resize((64, 64))).stddev[0]
        other_count = other_hash.bit_count()
        distance = (main_hash ^ other_hash).bit_count()
        # Reject low-detail/uniform comparisons and grossly different aspect ratios.
        if (main_gray >= 12 and other_std >= 12 and
                12 <= count <= 52 and 12 <= other_count <= 52 and distance <= 4):
            candidates.append({'reference_index': idx, 'observation': 'visual_similarity_candidate',
                               'distance_bits': distance})
    return {
        'status': 'completed',
        'finding': 'possible_duplicate_candidates' if candidates else 'no_candidates_at_current_settings',
        'references_compared': len(references), 'candidates': candidates,
        'method': 'sha256_exact_plus_uncalibrated_64bit_dhash_v1',
        'message': 'Only compared against explicitly supplied images in this request. '
                   'No candidate does not establish uniqueness; a candidate does not establish common identity, authorship or fraud.',
    }
