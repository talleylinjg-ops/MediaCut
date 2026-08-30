import io

import cv2
import numpy as np
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from app.config import IMAGE_ALLOWED_FORMATS, IMAGE_MAX_SIZE

FILTERS = {
    "gray",
    "blur",
    "sharpen",
    "edge",
    "emboss",
    "cinematic",
    "invert",
    "sepia",
    "warm",
    "cool",
    "pixelate",
    "vignette",
    "contrast",
    "sketch",
    "cartoon",
    "flip",
}
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
    h, w = arr.shape[:2]
    if filter_type == "gray":
        out = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return Image.fromarray(out).convert("RGB")
    if filter_type == "edge":
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        out = cv2.Canny(gray, 100, 200)
        return Image.fromarray(out).convert("RGB")
    if filter_type == "sketch":
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        inv = 255 - gray
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        out = cv2.divide(gray, 255 - blur, scale=256)
        return Image.fromarray(out).convert("RGB")
    if filter_type == "cinematic":
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.15, 0, 255).astype(np.uint8)
        hsv[:, :, 2] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(hsv[:, :, 2])
        out = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        out = cv2.convertScaleAbs(out, alpha=1.12, beta=8)
        out[:, :, 0] = np.clip(out[:, :, 0] * 1.06, 0, 255).astype(np.uint8)
        out[:, :, 2] = np.clip(out[:, :, 2] * 0.92, 0, 255).astype(np.uint8)
        return Image.fromarray(out)
    if filter_type == "invert":
        out = 255 - arr
    elif filter_type == "sepia":
        m = np.array([[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]])
        out = np.clip(arr @ m.T, 0, 255).astype(np.uint8)
    elif filter_type == "warm":
        out = arr.copy().astype(np.float32)
        out[:, :, 0] = np.clip(out[:, :, 0] * 1.15, 0, 255)
        out[:, :, 2] = np.clip(out[:, :, 2] * 0.88, 0, 255)
        out = out.astype(np.uint8)
    elif filter_type == "cool":
        out = arr.copy().astype(np.float32)
        out[:, :, 2] = np.clip(out[:, :, 2] * 1.15, 0, 255)
        out[:, :, 0] = np.clip(out[:, :, 0] * 0.9, 0, 255)
        out = out.astype(np.uint8)
    elif filter_type == "pixelate":
        sw = max(8, w // 12)
        sh = max(8, h // 12)
        small = cv2.resize(arr, (sw, sh), interpolation=cv2.INTER_LINEAR)
        out = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    elif filter_type == "vignette":
        y, x = np.ogrid[:h, :w]
        cx, cy = w / 2.0, h / 2.0
        dist = np.sqrt(((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2)
        mask = np.clip(1 - 0.55 * dist, 0, 1).astype(np.float32)
        out = (arr * mask[:, :, None]).astype(np.uint8)
    elif filter_type == "contrast":
        out = cv2.convertScaleAbs(arr, alpha=1.45, beta=-25)
    elif filter_type == "cartoon":
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(arr, 9, 150, 150)
        out = cv2.bitwise_and(color, color, mask=edges)
    elif filter_type == "flip":
        out = arr[:, ::-1]
    elif filter_type == "blur":
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
