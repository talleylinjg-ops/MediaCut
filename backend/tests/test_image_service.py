import io

import pytest
from fastapi import HTTPException
from PIL import Image

from app.services import image_service


def make_image(size=(200, 100), mode="RGB") -> bytes:
    img = Image.new(mode, size, (120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_validate_image_rejects_large_file():
    with pytest.raises(HTTPException) as exc:
        image_service.validate_image("image/png", image_service.IMAGE_MAX_SIZE + 1)
    assert exc.value.status_code == 413


def test_validate_image_rejects_bad_format():
    with pytest.raises(HTTPException) as exc:
        image_service.validate_image("application/pdf", 1024)
    assert exc.value.status_code == 400


def test_validate_image_accepts_valid():
    image_service.validate_image("image/png", 1024)


def test_crop():
    data = make_image()
    out, fmt = image_service.process_image(data, {"crop": [0, 0, 50, 50]})
    img = Image.open(io.BytesIO(out))
    assert img.size == (50, 50)
    assert fmt == "png"


def test_crop_invalid_box_raises():
    data = make_image()
    with pytest.raises(HTTPException):
        image_service.process_image(data, {"crop": [100, 100, 50, 50]})


def test_resize():
    data = make_image()
    out, _ = image_service.process_image(data, {"resize": {"width": 400, "height": 200}})
    img = Image.open(io.BytesIO(out))
    assert img.size == (400, 200)


def test_all_filters():
    data = make_image()
    for f in image_service.FILTERS:
        out, _ = image_service.process_image(data, {"filter": f})
        img = Image.open(io.BytesIO(out))
        assert img.size == (200, 100)


def test_unknown_filter_raises():
    data = make_image()
    with pytest.raises(HTTPException) as exc:
        image_service.process_image(data, {"filter": "rainbow"})
    assert exc.value.status_code == 400


def test_watermark():
    data = make_image()
    out, _ = image_service.process_image(
        data, {"watermark": {"text": "WM", "position": [10, 10], "size": 20}}
    )
    img = Image.open(io.BytesIO(out))
    assert img.size == (200, 100)


def test_convert_to_jpeg():
    data = make_image()
    out, fmt = image_service.process_image(data, {"output_format": "jpeg"})
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG"
    assert fmt == "jpeg"


def test_process_combo_crop_resize_filter():
    data = make_image()
    out, _ = image_service.process_image(
        data,
        {
            "crop": [0, 0, 100, 100],
            "resize": {"width": 50, "height": 50},
            "filter": "gray",
        },
    )
    img = Image.open(io.BytesIO(out))
    assert img.size == (50, 50)


def test_invalid_image_data_raises():
    with pytest.raises(HTTPException):
        image_service.process_image(b"not-an-image", {})
