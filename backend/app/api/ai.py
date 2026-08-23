import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import RESULT_DIR, UPLOAD_DIR
from app.core import billing, quota, task_queue
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
    quota.check_quota(db, developer, price)

    params: dict = {"text": text or ""}

    if voice is not None:
        audio_service.validate_audio(voice.content_type or "", voice.size or 0)
        ext = (voice.filename or "voice.wav").rsplit(".", 1)[-1].lower() or "wav"
        params["voice_path"] = _save_upload(voice, ext)

    if media is not None:
        content_type = media.content_type or ""
        if content_type.startswith("image/"):
            image_service.validate_image(content_type, media.size or 0)
            params["media_kind"] = "image"
            ext = (media.filename or "media.png").rsplit(".", 1)[-1].lower() or "png"
        elif content_type.startswith("audio/"):
            audio_service.validate_audio(content_type, media.size or 0)
            params["media_kind"] = "audio"
            ext = (media.filename or "media.wav").rsplit(".", 1)[-1].lower() or "wav"
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
        ext = (file.filename or "image.png").rsplit(".", 1)[-1].lower() or "png"
        input_path = _save_upload(file, ext)
    elif task_type == "asr":
        if file is None:
            raise HTTPException(status_code=400, detail="audio file is required")
        audio_service.validate_audio(file.content_type or "", file.size or 0)
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
