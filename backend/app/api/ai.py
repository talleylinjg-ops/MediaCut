import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import RESULT_DIR, UPLOAD_DIR
from app.core import billing, channels, quota, task_queue
from app.core.security import authenticate_developer
from app.database import get_db
from app.models import Developer
from app.schemas import TaskSubmitResponse
from app.services import ai_service, audio_service, image_service

router = APIRouter(prefix="/api/v1/ai", tags=["AI 能力"])


def _save_upload(file: UploadFile, ext: str) -> str:
    filename = f"upload_{uuid.uuid4().hex}.{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return path


@router.post("/chat", response_model=TaskSubmitResponse)
def submit_chat(
    text: str = Form(None),
    voice: UploadFile = File(None),
    media: UploadFile = File(None),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    has_input = bool((text or "").strip()) or voice is not None or media is not None
    if not has_input:
        raise HTTPException(status_code=400, detail="text, voice or media is required")

    price = billing.get_price("/api/v1/ai/chat")
    if any(channels.has_free(cap) for cap in ("chat", "t2i", "i2i")):
        price = 0
    quota.check_quota(db, developer, price)

    params: dict = {"text": text or ""}

    if voice is not None:
        audio_service.validate_audio(voice.content_type or "", voice.size or 0)
        ext = (voice.filename or "voice.wav").rsplit(".", 1)[-1].lower() or "wav"
        params["voice_path"] = _save_upload(voice, ext)

    if media is not None:
        content_type = media.content_type or ""
        ext = (media.filename or "").rsplit(".", 1)[-1].lower()
        if content_type.startswith("image/") or ext in image_service.EXT_ALLOWED:
            image_service.validate_image(content_type, media.size or 0)
            params["media_kind"] = "image"
            ext = ext or "png"
        elif content_type.startswith("audio/") or ext in audio_service.EXT_ALLOWED:
            audio_service.validate_audio(content_type, media.size or 0, ext)
            params["media_kind"] = "audio"
            ext = ext or "wav"
        else:
            raise HTTPException(status_code=400, detail="media must be image or audio")
        params["media_ext"] = ext
        params["media_path"] = _save_upload(media, ext)

    task_id = task_queue.create_task(developer.id, "chat", params)
    quota.consume_quota(db, developer, price)

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/api/v1/tasks/{task_id}",
    )


@router.post("/i2i", response_model=TaskSubmitResponse)
def submit_i2i(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    price = billing.get_price("/api/v1/ai/i2i")
    if channels.has_free("i2i"):
        price = 0
    quota.check_quota(db, developer, price)

    image_service.validate_image(file.content_type or "", file.size or 0)
    ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower() or "png"
    input_path = _save_upload(file, ext)

    task_id = task_queue.create_task(developer.id, "i2i", {"input_path": input_path, "prompt": prompt})
    quota.consume_quota(db, developer, price)

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/api/v1/tasks/{task_id}",
    )


@router.post("/t2i", response_model=TaskSubmitResponse)
def submit_t2i(
    prompt: str = Form(...),
    width: int = Form(None),
    height: int = Form(None),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    price = billing.get_price("/api/v1/ai/t2i")
    if channels.has_free("t2i"):
        price = 0
    quota.check_quota(db, developer, price)

    params: dict = {"prompt": prompt}
    if width:
        params["width"] = width
    if height:
        params["height"] = height

    task_id = task_queue.create_task(developer.id, "t2i", params)
    quota.consume_quota(db, developer, price)

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/api/v1/tasks/{task_id}",
    )


@router.post("/video", response_model=TaskSubmitResponse)
def submit_video(
    prompt: str = Form(...),
    duration: int = Form(5),
    motion: str = Form("zoom"),
    width: int = Form(None),
    height: int = Form(None),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    prompt = (prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    duration = max(1, min(int(duration or 5), 120))
    if motion not in ("zoom", "pan"):
        motion = "zoom"

    price = billing.get_price("/api/v1/ai/video")
    if channels.has_free("t2i"):
        price = 0
    quota.check_quota(db, developer, price)

    params: dict = {"prompt": prompt, "duration": duration, "motion": motion}
    if width:
        params["width"] = width
    if height:
        params["height"] = height

    task_id = task_queue.create_task(developer.id, "video", params)
    quota.consume_quota(db, developer, price)

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/api/v1/tasks/{task_id}",
    )


@router.post("/{task_type}", response_model=TaskSubmitResponse)
def submit_task(
    task_type: str,
    file: UploadFile = File(None),
    text: str = Form(None),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    if task_type not in ai_service.TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported task type: {task_type}")

    price = billing.get_price(f"/api/v1/ai/{task_type}")
    quota.check_quota(db, developer, price)

    if task_type in ("matting", "enhance"):
        if file is None:
            raise HTTPException(status_code=400, detail="image file is required")
        image_service.validate_image(file.content_type or "", file.size or 0)
        missing = ai_service.local_model_missing(task_type)
        if missing:
            raise HTTPException(status_code=503, detail=missing)
        ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower() or "png"
        input_path = _save_upload(file, ext)
    elif task_type == "asr":
        if file is None:
            raise HTTPException(status_code=400, detail="audio file is required")
        audio_service.validate_audio(file.content_type or "", file.size or 0)
        missing = ai_service.local_model_missing(task_type)
        if missing:
            raise HTTPException(status_code=503, detail=missing)
        ext = (file.filename or "audio.wav").rsplit(".", 1)[-1].lower() or "wav"
        input_path = _save_upload(file, ext)
    else:
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="text is required for tts")
        input_path = ""

    params = {"input_path": input_path} if input_path else {"text": text}

    task_id = task_queue.create_task(developer.id, task_type, params)
    quota.consume_quota(db, developer, price)

    return TaskSubmitResponse(
        task_id=task_id,
        status="pending",
        status_url=f"/api/v1/tasks/{task_id}",
    )
