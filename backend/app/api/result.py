import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.config import RESULT_DIR
from app.core import storage
from app.core.security import authenticate_developer
from app.database import get_db
from app.models import Developer, Task

router = APIRouter(prefix="/api/v1/result", tags=["结果下载"])

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".txt": "text/plain",
    ".mp4": "video/mp4",
}


@router.get("/{task_id}/{filename}")
def download_result(
    task_id: str,
    filename: str,
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(
        Task.task_id == task_id,
        Task.developer_id == developer.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")

    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="invalid filename")

    path = os.path.join(RESULT_DIR, task_id, filename)

    redirect_url = storage.signed_file_url(task_id, filename)
    if redirect_url:
        return RedirectResponse(redirect_url, status_code=302)

    if not os.path.isfile(path):
        data = storage.fetch_result(task_id, filename)
        if data is None:
            raise HTTPException(status_code=404, detail="result file not found")
        ext = os.path.splitext(filename)[1].lower()
        return Response(content=data, media_type=MIME_MAP.get(ext, "application/octet-stream"))

    ext = os.path.splitext(filename)[1].lower()
    return FileResponse(path, media_type=MIME_MAP.get(ext, "application/octet-stream"))
