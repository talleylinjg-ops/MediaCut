import json
import os
import subprocess
import uuid

import numpy as np

from fastapi import HTTPException

from app.core import channels
from app.services import video_service

TASK_TYPES = {"matting", "enhance", "asr", "tts", "t2i", "i2i", "video"}


def _ensure_wav(input_path: str, output_dir: str) -> str:
    if input_path.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):
        return input_path
    wav_path = os.path.join(output_dir, f"asr_{uuid.uuid4().hex}.wav")
    cmd = ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", wav_path]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise HTTPException(status_code=400, detail="unable to decode audio for ASR")
    return wav_path


_matting_session = None


def _get_matting_session():
    global _matting_session
    if _matting_session is None:
        from rembg import new_session

        _matting_session = new_session("u2net")
    return _matting_session


def run_matting(input_path: str, output_dir: str) -> str:
    from rembg import remove

    with open(input_path, "rb") as f:
        data = remove(f.read(), session=_get_matting_session())
    filename = f"result_{uuid.uuid4().hex}.png"
    with open(os.path.join(output_dir, filename), "wb") as f:
        f.write(data)
    return filename


def run_enhance(input_path: str, output_dir: str) -> str:
    import cv2

    img = cv2.imread(input_path)
    if img is None:
        raise HTTPException(status_code=400, detail="unable to read image for enhance")
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 3, 3, 7, 21)
    enhanced = cv2.detailEnhance(denoised, sigma_s=10, sigma_r=0.15)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    sharpened = cv2.filter2D(enhanced, -1, kernel)
    filename = f"result_{uuid.uuid4().hex}.png"
    path = os.path.join(output_dir, filename)
    cv2.imwrite(path, sharpened)
    return filename


_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        size = os.getenv("WHISPER_MODEL", "small")
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
    return _whisper_model


def run_asr(input_path: str, output_dir: str) -> dict:
    try:
        segments, _ = _get_whisper().transcribe(input_path, beam_size=5)
    except Exception:
        wav_path = _ensure_wav(input_path, output_dir)
        segments, _ = _get_whisper().transcribe(wav_path, beam_size=5)
    text = "".join(seg.text for seg in segments).strip()
    filename = f"result_{uuid.uuid4().hex}.txt"
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(text)
    return {"filename": filename, "text": text}


def run_tts(text: str, output_dir: str) -> str:
    import asyncio

    import edge_tts

    voice = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    filename = f"result_{uuid.uuid4().hex}.mp3"
    path = os.path.join(output_dir, filename)

    async def _synthesize():
        communicator = edge_tts.Communicate(text, voice)
        await communicator.save(path)

    asyncio.run(_synthesize())
    return filename


POLLINATIONS_IMG_URL = "https://image.pollinations.ai/prompt/{prompt}"
MODELSCOPE_T2I_URL = "https://api-inference.modelscope.cn/v1/images/generations"
MODELSCOPE_TASK_URL = "https://api-inference.modelscope.cn/v1/tasks/{task_id}"
T2I_MODEL = "Qwen/Qwen-Image"
I2I_MODEL = "Qwen/Qwen-Image-Edit"
I2I_FALLBACK_MODEL = "Qwen/Qwen-Image"
I2I_IMAGE_MAX_EDGE = 1280
I2I_OUTPUT_SIZE = "1024x1024"

_T2I_BLOCKED_KEYWORDS = (
    "裸体",
    "nude",
    "露点",
    "性交",
    "色情",
    "porn",
    "儿童色情",
    "暴力血腥",
    "自残",
    "自杀教程",
    "制作炸弹",
)


def _is_safe_t2i_prompt(prompt: str) -> bool:
    low = prompt.lower()
    return not any(kw in low for kw in _T2I_BLOCKED_KEYWORDS)


def _save_image_bytes(data: bytes, output_dir: str) -> str:
    from io import BytesIO

    from PIL import Image

    img = Image.open(BytesIO(data))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")
    filename = f"result_{uuid.uuid4().hex}.png"
    img.save(os.path.join(output_dir, filename))
    return filename


def _t2i_pollinations(prompt: str, width: int, height: int) -> bytes:
    import httpx

    from urllib.parse import quote

    url = POLLINATIONS_IMG_URL.format(prompt=quote(prompt))
    resp = httpx.get(
        url,
        params={"width": width, "height": height, "nologo": "true", "seed": uuid.uuid4().int % (2**31)},
        timeout=90,
        follow_redirects=True,
    )
    resp.raise_for_status()
    return resp.content


def _modelscope_error_detail(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    err = payload.get("error")
    if isinstance(err, dict):
        return err.get("message") or err.get("code") or ""
    if isinstance(err, str):
        return err
    return payload.get("message") or payload.get("detail") or ""


def _modelscope_poll_image(headers: dict, task_id: str, label: str) -> bytes:
    import time

    import httpx

    deadline = time.time() + 300
    while time.time() < deadline:
        time.sleep(5)
        query = httpx.get(
            MODELSCOPE_TASK_URL.format(task_id=task_id),
            headers={**headers, "X-ModelScope-Task-Type": "image_generation"},
            timeout=30,
        )
        query.raise_for_status()
        data = query.json()
        status = data.get("task_status")
        if status == "SUCCEED":
            outputs = data.get("output_images") or []
            if not outputs:
                raise HTTPException(status_code=502, detail=f"{label}失败：未返回图片数据")
            image_resp = httpx.get(outputs[0], timeout=120, follow_redirects=True)
            image_resp.raise_for_status()
            return image_resp.content
        if status == "FAILED":
            detail = _modelscope_error_detail(data.get("errors"))
            raise HTTPException(
                status_code=502, detail=f"{label}失败：{detail or '内容被拒绝或任务异常，请调整描述后重试'}"
            )
    raise HTTPException(status_code=504, detail=f"{label}超时，请稍后重试")


def _t2i_modelscope(prompt: str, width: int, height: int) -> bytes:
    import base64
    import httpx

    from app.core.settings import get_modelscope_token

    token = get_modelscope_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="图像生成服务暂不可用：免费生成源连接失败，且未配置 ModelScope Token（可在管理后台可选填写）",
        )
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"model": T2I_MODEL, "prompt": prompt, "size": f"{width}x{height}"}
    resp = httpx.post(
        MODELSCOPE_T2I_URL,
        json=payload,
        headers={**headers, "X-ModelScope-Async-Mode": "true"},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    items = body.get("data") if isinstance(body, dict) else None
    if items:
        item = items[0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            image_resp = httpx.get(item["url"], timeout=120, follow_redirects=True)
            image_resp.raise_for_status()
            return image_resp.content
    task_id = body.get("task_id") if isinstance(body, dict) else None
    if task_id:
        return _modelscope_poll_image(headers, task_id, "图像生成")
    raise HTTPException(
        status_code=502,
        detail=f"图像生成失败：{_modelscope_error_detail(body) or '生成服务返回数据格式异常，请稍后重试'}",
    )



def _channel_headers(channel: dict) -> dict:
    if channel.get("api_key"):
        return {"Authorization": f"Bearer {channel['api_key']}"}
    return {}


def _channel_image_bytes(payload: dict) -> bytes:
    import base64
    import httpx

    items = payload.get("data") if isinstance(payload, dict) else None
    if not items:
        detail = _modelscope_error_detail(payload)
        raise HTTPException(
            status_code=502, detail=f"生成渠道返回异常：{detail or '返回数据格式不正确'}"
        )
    item = items[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if not item.get("url"):
        raise HTTPException(status_code=502, detail="生成渠道未返回图片数据")
    image_resp = httpx.get(item["url"], timeout=120, follow_redirects=True)
    image_resp.raise_for_status()
    return image_resp.content


def _channel_t2i(channel: dict, prompt: str, width: int, height: int) -> bytes:
    import httpx

    base = channel["base_url"].rstrip("/")
    payload = {"model": channel.get("model_id") or "", "prompt": prompt, "size": f"{width}x{height}"}
    resp = httpx.post(
        f"{base}/images/generations",
        json=payload,
        headers=_channel_headers(channel),
        timeout=120,
    )
    resp.raise_for_status()
    return _channel_image_bytes(resp.json())


def _channel_i2i(channel: dict, image_uri: str, prompt: str) -> bytes:
    import httpx

    base = channel["base_url"].rstrip("/")
    payload = {
        "model": channel.get("model_id") or "",
        "prompt": prompt,
        "image": image_uri,
        "size": I2I_OUTPUT_SIZE,
    }
    resp = httpx.post(
        f"{base}/images/edits",
        json=payload,
        headers=_channel_headers(channel),
        timeout=300,
    )
    resp.raise_for_status()
    return _channel_image_bytes(resp.json())


def run_t2i(prompt: str, output_dir: str, width: int = 1024, height: int = 1024) -> str:
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="生成图片需要描述内容")
    if not _is_safe_t2i_prompt(prompt):
        raise HTTPException(status_code=400, detail="该描述包含不允许生成的内容，请调整后重试")
    for channel in channels.resolve("t2i"):
        try:
            data = _channel_t2i(channel, prompt, width, height)
            return _save_image_bytes(data, output_dir)
        except Exception:
            continue
    sizes = []
    for pair in ((width, height), (768, 768), (512, 512)):
        if pair[0] and pair[1] and pair not in sizes:
            sizes.append(pair)
    for w, h in sizes:
        try:
            return _save_image_bytes(_t2i_pollinations(prompt, w, h), output_dir)
        except Exception:
            continue
    return _save_image_bytes(_t2i_modelscope(prompt, width, height), output_dir)


_IMAGE_MIME_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def _image_to_data_uri(input_path: str) -> str:
    import base64

    from io import BytesIO

    from PIL import Image

    ext = os.path.splitext(input_path)[1].lower()
    raw_size = os.path.getsize(input_path)
    with Image.open(input_path) as img:
        max_edge = max(img.size)
        if ext in (".webp", ".bmp", ".gif") or max_edge > I2I_IMAGE_MAX_EDGE or raw_size > 4 * 1024 * 1024:
            rgb = img.convert("RGB")
            if max_edge > I2I_IMAGE_MAX_EDGE:
                ratio = I2I_IMAGE_MAX_EDGE / max_edge
                rgb = rgb.resize(
                    (max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS
                )
            buf = BytesIO()
            rgb.save(buf, "JPEG", quality=90)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    with open(input_path, "rb") as f:
        raw = f.read()
    mime = _IMAGE_MIME_MAP.get(ext, "image/png")
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def _modelscope_image_edit(image_uri: str, prompt: str, model: str) -> bytes:
    import httpx

    from app.core.settings import get_modelscope_token

    token = get_modelscope_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="云端图像编辑暂不可用：未配置 ModelScope Token（可在管理后台可选填写）",
        )
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "model": model,
        "prompt": prompt,
        "image_url": image_uri,
        "size": I2I_OUTPUT_SIZE,
    }
    resp = httpx.post(
        MODELSCOPE_T2I_URL,
        json=payload,
        headers={**headers, "X-ModelScope-Async-Mode": "true"},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    task_id = body.get("task_id") if isinstance(body, dict) else None
    if not task_id:
        raise HTTPException(
            status_code=502,
            detail=f"云端图像编辑失败：{_modelscope_error_detail(body) or '未取得任务 ID，请稍后重试'}",
        )
    return _modelscope_poll_image(headers, task_id, "云端图像编辑")


def run_i2i(input_path: str, prompt: str, output_dir: str) -> str:
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="需要说明要如何修改图片")
    if not _is_safe_t2i_prompt(prompt):
        raise HTTPException(status_code=400, detail="该修改要求包含不允许的内容，请调整后重试")
    image_uri = _image_to_data_uri(input_path)
    for channel in channels.resolve("i2i"):
        try:
            data = _channel_i2i(channel, image_uri, prompt)
            return _save_image_bytes(data, output_dir)
        except Exception:
            continue
    last_error: HTTPException | None = None
    for model in (I2I_MODEL, I2I_FALLBACK_MODEL):
        try:
            data = _modelscope_image_edit(image_uri, prompt, model)
            return _save_image_bytes(data, output_dir)
        except HTTPException as exc:
            if exc.status_code == 503:
                raise
            last_error = exc
    if last_error is not None:
        raise last_error
    raise HTTPException(status_code=502, detail="云端图像编辑失败，请稍后重试")


def run_ai_task(task_type: str, params: dict, output_dir: str) -> dict:
    if task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported task type: {task_type}")

    if task_type == "t2i":
        prompt = (params.get("prompt") or "").strip()
        width = int(params.get("width") or 1024)
        height = int(params.get("height") or 1024)
        filename = run_t2i(prompt, output_dir, width, height)
        return {"filename": filename, "kind": "image", "text": "图片已生成"}

    if task_type == "i2i":
        input_path = params.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=400, detail="input file missing")
        prompt = (params.get("prompt") or "").strip()
        filename = run_i2i(input_path, prompt, output_dir)
        return {"filename": filename, "kind": "image", "text": "已基于原图生成修改效果"}

    if task_type == "video":
        prompt = (params.get("prompt") or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="text is required for video")
        duration = int(params.get("duration") or 5)
        motion = params.get("motion") or "zoom"
        if motion not in ("zoom", "pan"):
            motion = "zoom"
        width = int(params.get("width") or 1024)
        height = int(params.get("height") or 1024)
        image_name = run_t2i(prompt, output_dir, width, height)
        image_path = os.path.join(output_dir, image_name)
        filename = video_service.image_to_video(image_path, duration, output_dir, motion=motion)
        return {
            "filename": filename,
            "kind": "video",
            "text": "已由文本生成画面并添加镜头运镜。说明：这是文本先生成画面，再做镜头推拉/平移，画面内容本身不会运动。",
        }

    if task_type == "matting" or task_type == "enhance":
        input_path = params.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=400, detail="input file missing")
        filename = run_matting(input_path, output_dir) if task_type == "matting" else run_enhance(input_path, output_dir)
        return {"filename": filename, "kind": "image"}

    if task_type == "asr":
        input_path = params.get("input_path")
        if not input_path or not os.path.exists(input_path):
            raise HTTPException(status_code=400, detail="input file missing")
        result = run_asr(input_path, output_dir)
        return {"filename": result["filename"], "kind": "text", "text": result["text"]}

    text = params.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required for tts")
    filename = run_tts(text, output_dir)
    return {"filename": filename, "kind": "audio"}


def serialize_result(result: dict) -> str:
    return json.dumps(result)
