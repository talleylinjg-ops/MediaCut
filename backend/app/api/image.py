import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.core import quota
from app.core.security import authenticate_developer
from app.database import get_db
from app.models import Developer
from app.services import image_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/image", tags=["图片剪辑"])


@router.post("/edit")
def image_edit(
    file: UploadFile = File(...),
    params: str = Form("{}"),
    developer: Developer = Depends(authenticate_developer),
    db: Session = Depends(get_db),
):
    quota.check_quota(db, developer)
    image_service.validate_image(file.content_type or "", file.size or 0)
    data = file.file.read()
    try:
        parsed = json.loads(params) if params else {}
    except json.JSONDecodeError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="invalid params json")

    result, output_format = image_service.process_image(data, parsed)
    quota.consume_quota(db, developer)

    content_type = f"image/{output_format}"
    if output_format == "jpeg":
        content_type = "image/jpeg"
    return Response(
        content=result,
        media_type=content_type,
        headers={
            "X-Remaining-Quota": str(quota.remaining_quota(developer)),
        },
    )
