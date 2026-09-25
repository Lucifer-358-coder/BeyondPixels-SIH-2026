"""Validate actual image bytes; no original document is stored."""
from __future__ import annotations

from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 8 * 1024 * 1024
MAX_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class InvalidMedia(ValueError):
    pass


def open_document_image(data: bytes) -> Image.Image:
    if not data or len(data) > MAX_BYTES:
        raise InvalidMedia("Image must be nonempty and at most 8 MB")
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in ("JPEG", "PNG"):
                raise InvalidMedia("Only JPEG and PNG images are supported")
            if probe.width * probe.height > MAX_PIXELS:
                raise InvalidMedia("Image has too many pixels")
            probe.verify()
        with Image.open(BytesIO(data)) as decoded:
            output = ImageOps.exif_transpose(decoded).convert("RGB")
            output.load()
        return output
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise InvalidMedia("Invalid or unsafe image content") from exc
