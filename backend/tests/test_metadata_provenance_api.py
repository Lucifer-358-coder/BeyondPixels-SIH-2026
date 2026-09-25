import io
from PIL import Image
import app


def _jpeg_with_metadata():
    image = Image.new("RGB", (120, 80), "white")
    exif = Image.Exif()
    exif[305] = "BeyondPixels Synthetic Editor"
    out = io.BytesIO()
    image.save(out, format="JPEG", quality=90, exif=exif)
    return out.getvalue()


def test_screen_returns_metadata_provenance(monkeypatch):
    monkeypatch.setenv("BEYONDPIXELS_DEMO_TOKEN", "local-test-token")
    client = app.app.test_client()
    response = client.post(
        "/v1/screen",
        headers={"Authorization": "Bearer local-test-token"},
        data={"image": (io.BytesIO(_jpeg_with_metadata()), "metadata.jpg")},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["provenance"]["status"] == "completed"
    assert payload["provenance"]["finding"] == "software_tag_present"
    assert payload["provenance"]["software"] == "BeyondPixels Synthetic Editor"
    assert payload["image_generation"]["status"] == "not_applicable"
