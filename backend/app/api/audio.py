import json
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import RESULT_DIR
from app.core import billing, quota
from app.core.security import authenticate_developer
from app.database import get_db
from app.models import Developer
from app.services import audio_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/audio", tags=["音频剪辑"])


@router.post("/edit")
def audio_edit(
    file: UploadFile = File(...),
    params: str = Form("{}"),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    price = billing.get_price("/api/v1/audio/edit")
    source_ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    audio_service.validate_audio(file.content_type or "", file.size or 0, source_ext)
    quota.check_quota(db, developer, price)
    data = file.file.read()
    try:
        parsed = json.loads(params) if params else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid params json")

    output_path, output_format = audio_service.process_audio(data, parsed, source_ext, RESULT_DIR)
    quota.consume_quota(db, developer, price)

    content_type = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
    }.get(output_format, "application/octet-stream")

    return FileResponse(
        path=output_path,
        media_type=content_type,
        filename=f"result.{output_format}",
        headers={
            "X-Remaining-Quota": str(quota.remaining_quota(developer)),
            "X-Result-Path": os.path.basename(output_path),
        },
    )
