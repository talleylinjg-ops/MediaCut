from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import security
from app.core.security import generate_api_key, hash_api_key
from app.database import get_db
from app.models import Developer
from app.schemas import ApiKeyResponse, DeveloperRegister

router = APIRouter(prefix="/api/v1/dev", tags=["开发者"])


@router.post("/register", response_model=ApiKeyResponse)
def register(payload: DeveloperRegister, db: Session = Depends(get_db)):
    if not payload.name.strip() or not payload.email.strip():
        raise HTTPException(status_code=400, detail="name and email are required")
    api_key = generate_api_key()
    developer = Developer(
        name=payload.name.strip(),
        email=payload.email.strip(),
        api_key_hash=hash_api_key(api_key),
    )
    db.add(developer)
    db.commit()
    db.refresh(developer)
    return ApiKeyResponse(developer_id=developer.id, api_key=api_key)


@router.post("/reset-key", response_model=ApiKeyResponse)
def reset_key(payload: DeveloperRegister, db: Session = Depends(get_db)):
    developer = db.query(Developer).filter(
        Developer.name == payload.name.strip(),
        Developer.email == payload.email.strip(),
    ).first()
    if developer is None:
        raise HTTPException(status_code=404, detail="developer not found")
    api_key = generate_api_key()
    developer.api_key_hash = hash_api_key(api_key)
    db.commit()
    return ApiKeyResponse(developer_id=developer.id, api_key=api_key)
