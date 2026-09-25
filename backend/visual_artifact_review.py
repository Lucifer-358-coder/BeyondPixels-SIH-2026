"""Uncalibrated JPEG compression-residual diagnostic; NOT a forgery detector.

This is a strictly separate, single-upload exploratory signal. JPEG residuals
are affected by ordinary text, resizing, printing, and repeated compression;
no residual is evidence of manipulation without independent validation.
"""
from __future__ import annotations

from io import BytesIO
from PIL import Image, ImageChops, ImageStat

_METHOD = 'jpeg_recompression_residual_diagnostic_v1'
_NOTE = ('JPEG recompression differences also arise from ordinary text, graphics, '
         'resaving and compression. Diagnostic locations are NOT tampering '
         'detections, confidence scores, or evidence of authenticity.')


def _unassessed(reason: str) -> dict:
    return {'status': 'not_assessed', 'finding': 'inconclusive',
            'method': _METHOD, 'reason': reason, 'diagnostic_regions': 0,
            'top_regions': [], 'overlay_available': False,
            'standalone_forgery_detection': False, 'message': _NOTE}


def review_jpeg_residuals(image: Image.Image, source_bytes: bytes) -> dict:
    """Return bounded, explanatory JPEG diagnostic without a forgery verdict.

    PNG and other formats abstain. This diagnostic neither uses MRZ nor needs a
    second image. It deliberately NEVER emits a genuine/fake conclusion.
    """
    if not isinstance(source_bytes, bytes) or not source_bytes.startswith(b'\xff\xd8\xff'):
        return _unassessed('jpeg_only')
    try:
        width, height = image.size
        if width < 256 or height < 256 or width * height > 16_000_000:
            return _unassessed('unsupported_image_geometry')
        # Downsample to bound CPU and memory; locations refer to this resized
        # diagnostic only, not to claimed ground-truth forgery pixels.
        if max(width, height) > 1200:
            factor = 1200 / max(width, height)
            size = (max(1, round(width * factor)), max(1, round(height * factor)))
            rgb = image.convert('RGB').resize(size, Image.Resampling.LANCZOS)
        else:
            rgb = image.convert('RGB')
        recoded = BytesIO()
        rgb.save(recoded, format='JPEG', quality=90, subsampling=0)
        recoded.seek(0)
        with Image.open(recoded) as candidate:
            candidate.load()
            diff = ImageChops.difference(rgb, candidate.convert('RGB'))
        # One value per non-overlapping 48px tile (no original pixels returned).
        # Every tile is merely a compression diagnostic, NOT an edit proposal.
        tile = 48
        w, h = rgb.size
        scores = []
        for y in range(0, h, tile):
            for x in range(0, w, tile):
                rect = (x, y, min(w, x + tile), min(h, y + tile))
                patch = diff.crop(rect)
                if patch.width < tile // 2 or patch.height < tile // 2:
                    continue
                score = sum(ImageStat.Stat(patch).mean) / 3
                scores.append((score, rect))
        if len(scores) < 16:
            return _unassessed('insufficient_diagnostic_tiles')
        sorted_scores = sorted(s for s, _ in scores)
        median = sorted_scores[len(sorted_scores)//2]
        abs_dev = sorted(abs(v-median) for v in sorted_scores)
        mad = abs_dev[len(abs_dev)//2]
        # Exploratory relative contrasts only: avoid invented thresholds for
        # deciding whether a photograph/document has been manipulated.
        cutoff = max(median + 5 * mad, sorted_scores[min(len(scores)-1, int(.95 * len(scores)))])
        selected = sorted((row for row in scores if row[0] > cutoff and row[0] > 2),
                          key=lambda row: row[0], reverse=True)[:3]
        regions = [{'x': round(box[0]/w, 6), 'y': round(box[1]/h, 6),
                    'width': round((box[2]-box[0])/w, 6),
                    'height': round((box[3]-box[1])/h, 6),
                    'observation': 'relative_jpeg_recompression_residual'}
                   for _, box in selected]
        return {'status': 'completed', 'finding': 'diagnostic_only',
                'method': _METHOD, 'reason': 'jpeg_residuals_measured',
                'diagnostic_regions': len(regions), 'top_regions': regions,
                'overlay_available': False, 'standalone_forgery_detection': False,
                'message': _NOTE}
    except (OSError, ValueError, TypeError):
        return _unassessed('jpeg_diagnostic_failed')
