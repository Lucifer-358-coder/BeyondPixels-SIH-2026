"""Independent exploratory image descriptors (not AI/deepfake predictions).

These measurements are NOT trained or calibrated and MUST NOT be interpreted
as evidence of image generation, manipulation or document authenticity.
No identity, biometric template, or uploaded image is persisted.
"""
from __future__ import annotations

from io import BytesIO
import cv2
import numpy as np
from PIL import Image, ImageOps

DESCRIPTOR_VERSION = "exploratory-frequency-texture-v0.1"
MAX_ANALYSIS_SIDE = 512


def _safe_fraction(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator > 1e-12 else 0.0


def extract_exploratory_descriptors(image_bytes: bytes) -> dict:
    """Compute deterministic descriptive statistics from already-validated JPEG/PNG.

    Called only AFTER media.open_document_image has validated image bytes.
    Resize is intentionally consistent but makes results resolution-dependent.
    """
    with Image.open(BytesIO(image_bytes)) as source:
        rgb = ImageOps.exif_transpose(source).convert('RGB')
        rgb.thumbnail((MAX_ANALYSIS_SIDE, MAX_ANALYSIS_SIDE), Image.Resampling.LANCZOS)
        pixels = np.asarray(rgb, dtype=np.uint8)
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    if min(gray.shape) < 16:
        return {"status": "insufficient_resolution", "version": DESCRIPTOR_VERSION,
                "descriptors": {}, "used_for_prediction": False}

    # Spatial high-frequency content, across fixed Gaussian smoothing scales.
    # Dimensionless energy fractions, not likelihoods.
    variance = float(np.var(gray))
    spatial = {}
    for sigma, label in ((1.0, "fine"), (2.0, "medium"), (4.0, "coarse")):
        blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=sigma, sigmaY=sigma)
        residual = gray - blurred
        spatial[f"{label}_residual_energy_ratio"] = _safe_fraction(
            float(np.mean(residual * residual)), variance)

    # Hann window reduces boundary discontinuities; DC is excluded.
    h, w = gray.shape
    window = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    centered = (gray - float(np.mean(gray))) * window
    power = np.abs(np.fft.fftshift(np.fft.fft2(centered))) ** 2
    fy = np.fft.fftshift(np.fft.fftfreq(h))
    fx = np.fft.fftshift(np.fft.fftfreq(w))
    radius = np.sqrt(fy[:, None] ** 2 + fx[None, :] ** 2)
    non_dc = radius > 1.0 / min(h, w)
    total = float(np.sum(power[non_dc]))
    frequency = {
        'mid_band_energy_fraction': _safe_fraction(float(np.sum(power[(radius >= 0.08) & (radius < 0.20)])), total),
        'high_band_energy_fraction': _safe_fraction(float(np.sum(power[radius >= 0.20])), total),
    }
    values = {**spatial, **frequency}
    if not all(np.isfinite(v) and v >= 0 for v in values.values()):
        raise ValueError('Exploratory descriptors are not finite')
    return {
        'status': 'completed', 'version': DESCRIPTOR_VERSION,
        'descriptors': {k: round(float(v), 6) for k, v in values.items()},
        'analysis_dimensions': {'width': int(w), 'height': int(h)},
        'used_for_prediction': False,
        'interpretation': 'Uncalibrated image statistics; none indicates AI generation or deepfake on its own.',
        'limitations': ['Not trained or validated on genuine documents, deepfakes, or unseen generators.',
                        'Sensitive to resizing, compression, image content, and capture conditions.'],
    }
