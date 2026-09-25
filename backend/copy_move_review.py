"""Conservative single-image *copy-move candidate* diagnostic.

Detects internally repeated local texture, not text alteration, identity fraud,
portrait replacement, or general tampering. Never returns a forged/genuine verdict.
"""
from __future__ import annotations

from collections import defaultdict

import cv2
import numpy as np
from PIL import Image

_METHOD = 'orb_self_similarity_copy_move_v1'
_MESSAGE = ('Repeated local texture can occur naturally (patterns, printed graphics, '
            'text, stamps). A candidate is not proof of duplication or forgery; '
            'a negative or unavailable result cannot establish authenticity.')


def _abstain(reason: str, keypoints: int = 0) -> dict:
    return {
        'status': 'not_assessed', 'finding': 'inconclusive', 'method': _METHOD,
        'reason': reason, 'candidate_regions': 0, 'top_regions': [],
        'image_width': None, 'image_height': None, 'keypoints': keypoints,
        'overlay_available': False, 'general_forgery_detection': False,
        'message': _MESSAGE,
    }


def review_copy_move(image: Image.Image) -> dict:
    """Find approximate translation-consistent, spatially disjoint ORB matches.

    Bounded to 1200px max side, 1200 features, and 2 candidate region pairs.
    No network, model checkpoint, persistence or external files.
    """
    try:
        w0, h0 = image.size
        if min(w0, h0) < 256 or w0 * h0 > 16_000_000:
            return _abstain('unsupported_geometry')
        scale = min(1., 1200. / max(w0, h0))
        w, h = max(1, round(w0 * scale)), max(1, round(h0 * scale))
        gray = np.asarray(image.convert('L').resize((w, h), Image.Resampling.BILINEAR))
        if float(gray.std()) < 6:
            return _abstain('insufficient_texture')
        orb = cv2.ORB_create(nfeatures=1200, scaleFactor=1.2, nlevels=8,
                             edgeThreshold=20, patchSize=31, fastThreshold=12)
        keypoints, descriptors = orb.detectAndCompute(gray, None)
        count = len(keypoints)
        if descriptors is None or count < 70:
            return _abstain('insufficient_distinct_features', count)
        # Self nearest-neighbor search. Descriptor 0 distance is typically self;
        # retain candidates only if an independent descriptor is close and far away.
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn = matcher.knnMatch(descriptors, descriptors, k=5)
        groups: dict[tuple[int, int], list[tuple[float, float, float, float, int]]] = defaultdict(list)
        for i, neighbors in enumerate(knn):
            source = keypoints[i].pt
            eligible = []
            for m in neighbors:
                if m.trainIdx == i:
                    continue
                dest = keypoints[m.trainIdx].pt
                dx, dy = dest[0] - source[0], dest[1] - source[1]
                if dx * dx + dy * dy < 85 * 85:
                    continue
                if m.distance > 25:
                    continue
                eligible.append((m, dx, dy, dest))
            if not eligible:
                continue
            match, dx, dy, dest = min(eligible, key=lambda v: v[0].distance)
            # Orient all displacements consistently, avoiding mirrored bins.
            x1, y1, x2, y2 = (*source, *dest)
            if dx < 0 or (dx == 0 and dy < 0):
                dx, dy = -dx, -dy
                x1, y1, x2, y2 = x2, y2, x1, y1
            groups[(round(dx / 12), round(dy / 12))].append((x1, y1, x2, y2, match.distance))
        candidates = []
        for matches in groups.values():
            # Every two real matched points may appear twice (A->B and B->A).
            # Spatially diverse source coordinates and 8 distinct pairs required.
            unique = {}
            for x1, y1, x2, y2, dist in matches:
                pair = (round(x1 / 3), round(y1 / 3), round(x2 / 3), round(y2 / 3))
                unique[pair] = (x1, y1, x2, y2, dist)
            matches = list(unique.values())
            if len(matches) < 9:
                continue
            coords = np.asarray([m[:4] for m in matches], dtype=np.float32)
            # Refine translation consensus with the median residual (not arbitrary labels).
            shifts = coords[:, 2:4] - coords[:, 0:2]
            median = np.median(shifts, axis=0)
            inliers = np.max(abs(shifts - median), axis=1) < 9
            coords = coords[inliers]
            if len(coords) < 9:
                continue
            left = coords[:, :2]
            right = coords[:, 2:4]
            span = np.ptp(left, axis=0)
            if min(span) < 24 or span[0] * span[1] < 1500:
                continue
            rectangles = []
            for pts in (left, right):
                mn = np.maximum(0, np.floor(np.min(pts, axis=0) - 12)).astype(int)
                mx = np.minimum([w, h], np.ceil(np.max(pts, axis=0) + 12)).astype(int)
                if np.any(mx - mn < 20):
                    break
                rectangles.append({
                    'x': round(int(mn[0]) / w, 6), 'y': round(int(mn[1]) / h, 6),
                    'width': round(int(mx[0] - mn[0]) / w, 6),
                    'height': round(int(mx[1] - mn[1]) / h, 6),
                })
            if len(rectangles) == 2:
                # Reject two boxes that overlap: repeated letters, MRZ text and
                # regular page structures produce such translation clusters.
                a, b = rectangles
                x_overlap = min(a['x'] + a['width'], b['x'] + b['width']) - max(a['x'], b['x'])
                y_overlap = min(a['y'] + a['height'], b['y'] + b['height']) - max(a['y'], b['y'])
                if x_overlap > 0 and y_overlap > 0:
                    continue
                candidates.append((len(coords), rectangles))
        candidates.sort(key=lambda entry: entry[0], reverse=True)
        region_pairs = [boxes for _, boxes in candidates[:2]]
        # Empty means nothing supported by this diagnostic, NOT 'not tampered'.
        return {
            'status': 'completed',
            'finding': 'repeated_texture_candidate' if region_pairs else 'no_candidate_localized',
            'method': _METHOD,
            'reason': 'relative_self_similarity_only',
            'candidate_regions': len(region_pairs),
            'top_regions': [box for pair in region_pairs for box in pair],
            'image_width': w0, 'image_height': h0, 'keypoints': count,
            'overlay_available': bool(region_pairs), 'general_forgery_detection': False,
            'message': _MESSAGE,
        }
    except (cv2.error, OSError, ValueError, TypeError):
        return _abstain('copy_move_diagnostic_failed')
