import json
import os
import subprocess
import uuid

import numpy as np

from fastapi import HTTPException

TASK_TYPES = {"matting", "enhance", "asr", "tts"}


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
T2I_MODEL = "Qwen/Qwen-Image"

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
    payload = {"model": T2I_MODEL, "prompt": prompt, "size": f"{width}x{height}"}
    resp = httpx.post(
        MODELSCOPE_T2I_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    item = resp.json()["data"][0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    image_resp = httpx.get(item["url"], timeout=120, follow_redirects=True)
    image_resp.raise_for_status()
    return image_resp.content


def run_t2i(prompt: str, output_dir: str, width: int = 1024, height: int = 1024) -> str:
    if not prompt or not prompt.strip():
        raise HTTPException(status_code=400, detail="生成图片需要描述内容")
    if not _is_safe_t2i_prompt(prompt):
        raise HTTPException(status_code=400, detail="该描述包含不允许生成的内容，请调整后重试")
    try:
        data = _t2i_pollinations(prompt, width, height)
    except Exception:
        data = _t2i_modelscope(prompt, width, height)
    return _save_image_bytes(data, output_dir)


def run_ai_task(task_type: str, params: dict, output_dir: str) -> dict:
    if task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported task type: {task_type}")

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
