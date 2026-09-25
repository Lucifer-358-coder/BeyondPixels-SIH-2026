from io import BytesIO
from PIL import Image, PngImagePlugin
from metadata_provenance import inspect_file_metadata


def _jpeg_with_software():
    image = Image.new("RGB", (64, 48), "white")
    exif = Image.Exif()
    exif[305] = "BeyondPixels Synthetic Editor"
    exif[271] = "Synthetic Camera Co"
    exif[272] = "DemoCam 1"
    exif[306] = "2026:09:20 12:00:00"
    out = BytesIO()
    image.save(out, format="JPEG", quality=90, exif=exif)
    return out.getvalue()


def _plain_png():
    out = BytesIO()
    Image.new("RGB", (64, 48), "white").save(out, format="PNG")
    return out.getvalue()


def test_jpeg_metadata_is_reported_without_authenticity_claim():
    result = inspect_file_metadata(_jpeg_with_software())
    assert result["status"] == "completed"
    assert result["finding"] == "software_tag_present"
    assert result["software"] == "BeyondPixels Synthetic Editor"
    assert result["camera_make"] == "Synthetic Camera Co"
    assert result["camera_model"] == "DemoCam 1"
    assert result["metadata_present"] is True


def test_plain_png_abstains_from_provenance_claim():
    result = inspect_file_metadata(_plain_png())
    assert result["status"] == "completed"
    assert result["finding"] == "no_embedded_metadata"
    assert result["metadata_present"] is False


def test_marker_scan_is_presence_only():
    data = _plain_png() + b"c2pa"
    result = inspect_file_metadata(data)
    assert result["c2pa_marker_candidate"] is True
    assert "NOT validated" in result["message"]
