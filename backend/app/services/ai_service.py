import json
import os
import uuid

from fastapi import HTTPException

from app.config import MODELSCOPE_MODELS
from app.core.settings import get_modelscope_token

_pipelines = {}

TASK_TYPES = {"matting", "enhance", "asr", "tts"}


def _get_pipeline(task_type: str):
    token = get_modelscope_token()
    if not token:
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable: MODELSCOPE_API_TOKEN not configured",
        )
    os.environ["MODELSCOPE_API_TOKEN"] = token
    if task_type not in _pipelines:
        from modelscope import pipeline

        _pipelines[task_type] = pipeline(task_type, model=MODELSCOPE_MODELS[task_type])
    return _pipelines[task_type]


def _save_pil_image(image, output_dir: str) -> str:
    filename = f"result_{uuid.uuid4().hex}.png"
    path = os.path.join(output_dir, filename)
    image.save(path)
    return filename


def run_matting(input_path: str, output_dir: str) -> str:
    pipe = _get_pipeline("matting")
    result = pipe(input_path)
    image = result.get("output_img") if isinstance(result, dict) else result
    return _save_pil_image(image, output_dir)


def run_enhance(input_path: str, output_dir: str) -> str:
    pipe = _get_pipeline("enhance")
    result = pipe(input_path)
    image = result.get("output_img") if isinstance(result, dict) else result
    return _save_pil_image(image, output_dir)


def run_asr(input_path: str, output_dir: str) -> dict:
    pipe = _get_pipeline("asr")
    result = pipe(input_path)
    text = result.get("text") if isinstance(result, dict) else str(result)
    filename = f"result_{uuid.uuid4().hex}.txt"
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(text)
    return {"filename": filename, "text": text}


def run_tts(text: str, output_dir: str) -> str:
    pipe = _get_pipeline("tts")
    result = pipe(text)
    output = result.get("output") if isinstance(result, dict) else result
    filename = f"result_{uuid.uuid4().hex}.wav"
    output.save(os.path.join(output_dir, filename))
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
