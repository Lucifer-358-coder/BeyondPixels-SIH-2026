from io import BytesIO
import pytest
from PIL import Image
from media import InvalidMedia, MAX_BYTES, open_document_image


def test_valid_png():
    output = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(output, format='PNG')
    assert open_document_image(output.getvalue()).size == (20, 20)


def test_rejects_unrecognized_file():
    with pytest.raises(InvalidMedia):
        open_document_image(b'not an image')


def test_rejects_oversize():
    with pytest.raises(InvalidMedia):
        open_document_image(b'a' * (MAX_BYTES + 1))


def test_rejects_gif():
    output = BytesIO()
    Image.new('RGB', (20, 20), 'white').save(output, format='GIF')
    with pytest.raises(InvalidMedia):
        open_document_image(output.getvalue())
