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
