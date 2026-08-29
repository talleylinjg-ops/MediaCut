import io

import cv2
import numpy as np
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from app.config import IMAGE_ALLOWED_FORMATS, IMAGE_MAX_SIZE

FILTERS = {"gray", "blur", "sharpen", "edge", "emboss"}
OUTPUT_FORMATS = {"png", "jpeg", "webp", "bmp"}
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
EXT_ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp", "gif"}


def validate_image(content_type: str, size: int, source_ext: str = "") -> None:
    if size > IMAGE_MAX_SIZE:
        raise HTTPException(status_code=413, detail="file too large")
    if content_type in IMAGE_ALLOWED_FORMATS:
        return
    if source_ext and source_ext.lower() in EXT_ALLOWED:
        return
    raise HTTPException(status_code=400, detail="invalid file format")


def apply_crop(img: Image.Image, box) -> Image.Image:
    left, top, right, bottom = (int(v) for v in box)
    width, height = img.size
    left = max(0, left)
    top = max(0, top)
    right = min(width, right)
    bottom = min(height, bottom)
    if right <= left or bottom <= top:
        raise HTTPException(status_code=400, detail="invalid crop box")
    return img.crop((left, top, right, bottom))


def apply_resize(img: Image.Image, width, height) -> Image.Image:
    width = int(width or 0)
    height = int(height or 0)
    if width <= 0 and height <= 0:
        raise HTTPException(status_code=400, detail="resize requires width or height")
    if width <= 0:
        width = int(img.width * height / img.height)
    if height <= 0:
        height = int(img.height * width / img.width)
    if width <= 0 or height <= 0:
        raise HTTPException(status_code=400, detail="invalid resize size")
    return img.resize((int(width), int(height)), Image.LANCZOS)


def apply_filter(img: Image.Image, filter_type: str) -> Image.Image:
    if filter_type not in FILTERS:
        raise HTTPException(status_code=400, detail=f"unsupported filter: {filter_type}")
    arr = np.array(img.convert("RGB"))
    if filter_type == "gray":
        out = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return Image.fromarray(out).convert("RGB")
    if filter_type == "edge":
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        out = cv2.Canny(gray, 100, 200)
        return Image.fromarray(out).convert("RGB")
    if filter_type == "blur":
        out = cv2.GaussianBlur(arr, (0, 0), 2)
    elif filter_type == "sharpen":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        out = cv2.filter2D(arr, -1, kernel)
    elif filter_type == "emboss":
        kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
        out = cv2.filter2D(arr, -1, kernel)
    return Image.fromarray(out)


def apply_watermark(img: Image.Image, text: str, position, size: int, color) -> Image.Image:
    if not text:
        raise HTTPException(status_code=400, detail="watermark text is empty")
    overlay = img.copy()
    draw = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype(FONT_PATH, int(size))
    except OSError:
        font = ImageFont.load_default()
    x, y = position
    if isinstance(position, str) and position == "center":
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (img.width - tw) / 2 - bbox[0]
        y = (img.height - th) / 2 - bbox[1]
    draw.text((int(x), int(y)), text, fill=tuple(color), font=font)
    return Image.alpha_composite(img.convert("RGBA"), overlay.convert("RGBA")).convert(img.mode)


def process_image(data: bytes, params: dict) -> tuple[bytes, str]:
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid image file")

    if "crop" in params:
        img = apply_crop(img, params["crop"])
    if "resize" in params:
        img = apply_resize(img, params["resize"].get("width"), params["resize"].get("height"))
    if "filter" in params:
        img = apply_filter(img, params["filter"])
    if "watermark" in params:
        wm = params["watermark"]
        img = apply_watermark(
            img,
            wm.get("text", ""),
            wm.get("position", [0, 0]),
            wm.get("size", 24),
            tuple(wm.get("color", [255, 0, 0])),
        )

    output_format = params.get("output_format", "png")
    if output_format not in OUTPUT_FORMATS:
        raise HTTPException(status_code=400, detail=f"unsupported output format: {output_format}")

    if img.mode in ("RGBA", "LA", "P") and output_format == "jpeg":
        img = img.convert("RGB")

    buf = io.BytesIO()
    save_kwargs = {"format": output_format.upper()}
    if output_format == "jpeg":
        save_kwargs["quality"] = 92
    img.save(buf, **save_kwargs)
    return buf.getvalue(), output_format
