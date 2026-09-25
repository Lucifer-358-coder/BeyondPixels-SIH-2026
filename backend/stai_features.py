"""STAI-derived handcrafted forensic signal functions, independently packaged for BeyondPixels.

This is an exploratory baseline, NOT a detector of document validity or identity.
The five signals are weak hypotheses; their human-readable interpretations require
independent studies. Adapted from the user's existing STAI project without editing it.
"""
import cv2
import numpy as np
from scipy import stats
from itertools import combinations

# ─── Signal 1 : FFT Grid Artifact Score ──────────────────────────────────────

def _grid_artifact_score(gray: np.ndarray) -> float:
    """
    Measures periodic bright spots in the 2-D Fourier spectrum.
    These arise from the upsampling layers in GANs / diffusion models.
    Higher score → more grid artifacts → more likely AI.
    """
    f_shifted = np.fft.fftshift(np.fft.fft2(gray))
    magnitude = np.log1p(np.abs(f_shifted))

    h, w   = magnitude.shape
    cy, cx = h // 2, w // 2

    masked = magnitude.copy()
    masked[cy - 5 : cy + 5, :] = 0
    masked[:, cx - 5 : cx + 5] = 0

    Y, X = np.ogrid[:h, :w]
    centre_mask = (X - cx) ** 2 + (Y - cy) ** 2 < (min(h, w) // 8) ** 2
    masked[centre_mask] = 0

    flat = masked.ravel()
    flat = flat[flat > 0]
    if flat.size == 0:
        return 0.0

    return float(np.percentile(flat, 99) / (np.median(flat) + 1e-6))


# ─── Signal 2 : Radial Smoothness ────────────────────────────────────────────

def _radial_smoothness(gray: np.ndarray) -> float:
    """
    Std deviation of first-order differences in the radial frequency profile.
    Real photos: smooth decay. AI images: bumpy.
    """
    f_shifted = np.fft.fftshift(np.fft.fft2(gray))
    magnitude = np.log1p(np.abs(f_shifted))

    h, w   = magnitude.shape
    cy, cx = h // 2, w // 2
    max_r  = min(cy, cx)

    Y, X     = np.ogrid[:h, :w]
    dist_map = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2).astype(int)

    profile = [
        magnitude[dist_map == r].mean()
        for r in range(1, max_r)
        if (dist_map == r).any()
    ]

    if len(profile) < 2:
        return 0.0

    arr = np.array(profile, dtype=np.float32)
    arr /= arr.max() + 1e-6
    return float(np.std(np.diff(arr)))


# ─── Signal 3 : Noise Kurtosis ───────────────────────────────────────────────

def _noise_kurtosis(img: np.ndarray) -> float:
    """
    Kurtosis of the residual noise after NL-Means denoising.
    Real camera noise: high kurtosis (non-Gaussian).
    AI noise:          low kurtosis (near-Gaussian).
    """
    value, _ = _noise_kurtosis_with_std(img)
    return value


def _noise_kurtosis_with_std(img: np.ndarray) -> tuple[float, float]:
    """Return residual kurtosis and standard deviation for semantic gating."""
    gray_u8  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(
        gray_u8, None, h=10,
        templateWindowSize=7, searchWindowSize=21,
    )
    residual = gray_u8.astype(np.float32) - denoised.astype(np.float32)
    residual_std = float(np.std(residual))

    # NL-Means can reproduce highly textured input almost exactly, leaving an
    # unusably empty residual. Use a local high-pass residual in that case so
    # noise statistics still reflect the image rather than the denoiser's
    # behavior.
    if residual_std < 1.0 and float(np.std(gray_u8)) >= 1.0:
        local_mean = cv2.GaussianBlur(gray_u8, (3, 3), 0)
        residual = gray_u8.astype(np.float32) - local_mean.astype(np.float32)
        residual_std = float(np.std(residual))

    flat = residual.ravel()
    # Constant/near-constant residuals have undefined kurtosis; treat them as
    # zero excess kurtosis rather than propagating NaN through the classifier.
    if flat.size < 2 or residual_std < 1e-12:
        return 0.0, residual_std
    value = float(stats.kurtosis(flat, fisher=True, bias=False))
    return (value if np.isfinite(value) else 0.0), residual_std


# ─── Signal 4 : Vanishing Point Score ────────────────────────────────────────

def _vanishing_point_score(img: np.ndarray) -> dict:
    """
    Detects perspective vanishing points using the Hough line transform.

    In a real photograph, groups of parallel lines (edges of buildings,
    roads, furniture, etc.) converge toward one or more vanishing points
    that lie on the horizon line — a fundamental law of perspective geometry.

    AI-generated images frequently violate this because the model learns
    local texture patterns rather than global 3-D scene structure.

    Algorithm:
      1. Canny edge detection on a down-scaled grey image.
      2. Probabilistic Hough transform to find line segments.
      3. Extend each segment to a full infinite line (y = mx + b).
      4. Compute pairwise intersection points of all line pairs.
      5. Cluster intersections with DBSCAN-style binning.
      6. Score = size of largest cluster / total intersections.
         A high score means many lines agree on a single point → real photo.

    Returns:
        {
            "consistency":    float  0-1  (1 = perfect vanishing point)
            "line_count":     int
            "cluster_spread": float  (pixel radius of the best cluster)
        }
    """
    # ── Pre-process ──────────────────────────────────────────────────────────
    h, w  = img.shape[:2]
    scale = 640 / max(h, w)                    # work at ≤640px longest side
    small = cv2.resize(img, (int(w * scale), int(h * scale)))
    sh, sw = small.shape[:2]

    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (5, 5), 1.0)
    edges = cv2.Canny(blur, threshold1=50, threshold2=150, apertureSize=3)

    # ── Hough line segments ───────────────────────────────────────────────────
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=60,
        minLineLength=int(min(sh, sw) * 0.08),   # at least 8% of image size
        maxLineGap=int(min(sh, sw) * 0.03),
    )

    if lines is None or len(lines) < 4:
        # Too few lines to reason about perspective
        return {"consistency": 0.5, "line_count": 0, "cluster_spread": 0.0}

    segments = lines.reshape(-1, 4)          # shape (N, 4)  x1,y1,x2,y2

    # ── Filter near-horizontal and near-vertical lines ────────────────────────
    # (horizon-direction lines are the most informative for VP detection)
    useful = []
    for x1, y1, x2, y2 in segments:
        dx, dy = float(x2 - x1), float(y2 - y1)
        length = np.hypot(dx, dy)
        if length < 1:
            continue
        angle = abs(np.degrees(np.arctan2(dy, dx)))   # 0–180
        # Keep lines that are NOT close to perfectly horizontal/vertical
        # (those are degenerate for VP detection but add noise)
        if 10 < angle < 80 or 100 < angle < 170:
            useful.append((x1, y1, x2, y2, dx / length, dy / length))

    if len(useful) < 4:
        return {"consistency": 0.5, "line_count": len(segments), "cluster_spread": 0.0}

    # Cap at 60 lines to keep pairwise intersection O(N²) fast
    if len(useful) > 60:
        useful = useful[:60]

    # ── Pairwise intersections ────────────────────────────────────────────────
    intersections = []
    for (x1, y1, x2, y2, dx1, dy1), (x3, y3, x4, y4, dx2, dy2) in combinations(useful, 2):
        pt = _line_intersection(
            (float(x1), float(y1)), (float(x2), float(y2)),
            (float(x3), float(y3)), (float(x4), float(y4)),
        )
        if pt is None:
            continue
        px, py = pt
        # Allow intersections well outside the image (VP can be at infinity)
        margin = max(sh, sw) * 3
        if -margin < px < sw + margin and -margin < py < sh + margin:
            intersections.append((px, py))

    if len(intersections) < 3:
        return {"consistency": 0.5, "line_count": len(useful), "cluster_spread": float(sw)}

    # ── Cluster intersections (grid-based binning) ────────────────────────────
    pts   = np.array(intersections, dtype=np.float32)
    best_count, best_spread = _cluster_score(pts, bin_size=max(sh, sw) * 0.12)

    consistency    = best_count / len(intersections)
    cluster_spread = best_spread

    return {
        "consistency":    float(np.clip(consistency, 0.0, 1.0)),
        "line_count":     len(useful),
        "cluster_spread": float(cluster_spread),
    }


def _line_intersection(
    p1: tuple, p2: tuple,
    p3: tuple, p4: tuple,
) -> tuple | None:
    """
    Returns the intersection point of infinite lines through (p1,p2) and (p3,p4).
    Returns None if lines are parallel or nearly so.
    """
    x1, y1 = p1; x2, y2 = p2
    x3, y3 = p3; x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    px = x1 + t * (x2 - x1)
    py = y1 + t * (y2 - y1)
    return (px, py)


def _cluster_score(pts: np.ndarray, bin_size: float) -> tuple[int, float]:
    """
    Fast grid-based density estimation.
    Returns (count_in_best_bin, spread_of_best_bin).
    """
    xs = (pts[:, 0] / bin_size).astype(int)
    ys = (pts[:, 1] / bin_size).astype(int)

    cell_counts: dict[tuple, list] = {}
    for i, (cx, cy) in enumerate(zip(xs, ys)):
        key = (int(cx), int(cy))
        cell_counts.setdefault(key, []).append(i)

    best_key  = max(cell_counts, key=lambda k: len(cell_counts[k]))
    best_idxs = cell_counts[best_key]
    best_pts  = pts[best_idxs]

    spread = float(np.std(best_pts)) if len(best_pts) > 1 else 0.0
    return len(best_idxs), spread


# ─── Signal 5 : Shadow Consistency Score ─────────────────────────────────────

def _shadow_consistency_score(img: np.ndarray) -> dict:
    """
    Analyses shadow direction consistency across an image.

    In a real photo every shadow is cast by the same light source, so all
    shadow edges point in roughly the same direction (away from the source).
    AI images generate shadows locally — the model fills in plausible-looking
    dark regions without enforcing global light-source coherence, producing
    shadows that point in contradictory directions.

    Algorithm:
      1. Convert to LAB colour space — the L channel isolates luminance.
      2. Detect dark regions (shadows) using adaptive thresholding on L.
      3. Find contours of shadow regions and compute their minimum-area
         bounding box orientation (angle of the long axis).
      4. Collect all orientation angles → measure their circular std deviation.
         Low circular std  → all shadows aligned  → single light source → real.
         High circular std → shadows point all over the place → AI.
      5. Consistency = 1 − (circular_std / 90°)  clamped to 0-1.

    Returns:
        {
            "consistency":    float  0-1
            "angle_std":      float  (degrees, circular std of shadow angles)
            "region_count":   int    (number of shadow regions analysed)
        }
    """
    h, w  = img.shape[:2]
    scale = 640 / max(h, w)
    small = cv2.resize(img, (int(w * scale), int(h * scale)))

    # ── Isolate luminance ─────────────────────────────────────────────────────
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB)
    L   = lab[:, :, 0]   # 0-255

    # ── Shadow mask: dark areas (low luminance) ───────────────────────────────
    # Adaptive threshold finds locally dark regions even in unevenly lit scenes
    shadow_mask = cv2.adaptiveThreshold(
        L, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=51,
        C=10,
    )

    # Clean up noise
    kernel      = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    shadow_mask = cv2.morphologyEx(shadow_mask, cv2.MORPH_OPEN,  kernel, iterations=2)
    shadow_mask = cv2.morphologyEx(shadow_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # ── Find shadow region contours ───────────────────────────────────────────
    contours, _ = cv2.findContours(
        shadow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    min_area = (small.shape[0] * small.shape[1]) * 0.002   # at least 0.2% of image
    angles   = []

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        # Minimum area bounding rectangle → gives orientation angle
        rect  = cv2.minAreaRect(cnt)
        angle = rect[2]   # OpenCV returns -90 to 0

        # Normalise to 0-180° (shadow direction is ambiguous by 180°)
        if angle < -45:
            angle += 90
        angle = angle % 180
        angles.append(angle)

    if len(angles) < 3:
        # Too few shadow regions to measure consistency
        return {"consistency": 0.5, "angle_std": 0.0, "region_count": len(angles)}

    # ── Circular statistics on angles ─────────────────────────────────────────
    # Convert angles to unit-circle vectors, then measure vector coherence
    rad       = np.deg2rad(np.array(angles) * 2)   # double angle trick for 180° ambiguity
    mean_cos  = np.mean(np.cos(rad))
    mean_sin  = np.mean(np.sin(rad))
    R         = np.hypot(mean_cos, mean_sin)        # resultant length 0-1

    # R close to 1 → all angles aligned; R close to 0 → random directions
    # Circular std approximation: σ = sqrt(-2 * ln(R))  (in radians)
    R = float(np.clip(R, 1e-12, 1.0))
    circular_std_rad = np.sqrt(-2 * np.log(R))
    circular_std_deg = float(np.degrees(circular_std_rad) / 2)  # undo double-angle

    # Consistency: low std → high consistency → real photo
    # Empirical ceiling: std > 45° is fully inconsistent
    consistency = float(np.clip(1.0 - (circular_std_deg / 45.0), 0.0, 1.0))

    return {
        "consistency":  consistency,
        "angle_std":    round(circular_std_deg, 2),
        "region_count": len(angles),
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _decode(image_bytes: bytes) -> np.ndarray:
    """Decode raw bytes → BGR numpy array."""
    if not image_bytes:
        raise ValueError("Could not decode image. Ensure it is a valid JPG/PNG/WEBP.")
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    try:
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise ValueError("Could not decode image. Ensure it is a valid JPG/PNG/WEBP.") from exc
    if img is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPG/PNG/WEBP.")
    return img


FEATURE_NAMES = ("grid_norm", "radial_norm", "kurtosis_norm", "vanishing_norm", "shadow_norm")

def extract_stai_features(image_bytes: bytes) -> tuple[np.ndarray, dict]:
    """Return feature vector in exact CIFAKE training order and observational signals."""
    img = _decode(image_bytes)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    grid = _grid_artifact_score(gray)
    radial = _radial_smoothness(gray)
    kurtosis, residual_std = _noise_kurtosis_with_std(img)
    vp = _vanishing_point_score(img)
    shadow = _shadow_consistency_score(img)
    vector = np.asarray([
        min(grid / 15.0, 1.0),
        min(radial / 0.03, 1.0),
        0.40 if residual_std < 1.0 else 1.0 / (1.0 + abs(kurtosis) / 10.0),
        1.0 - vp['consistency'],
        1.0 - shadow['consistency'],
    ], dtype=np.float64)
    if not np.isfinite(vector).all() or np.min(vector)<0 or np.max(vector)>1:
        raise ValueError('Image features cannot be computed safely')
    observations = {
        'signal_scores':dict(zip(FEATURE_NAMES,[round(float(v),4) for v in vector])),
        'noise_residual_std':round(float(residual_std),4),
        'perspective_inconclusive':vp['line_count']==0,
        'shadow_inconclusive':shadow['region_count']<3,
    }
    return vector.reshape(1,-1), observations
