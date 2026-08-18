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
