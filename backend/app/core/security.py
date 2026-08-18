import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, Header, HTTPException, status
from jwt import InvalidTokenError, decode, encode
from sqlalchemy.orm import Session

from app import models
from app.config import ADMIN_PASSWORD, ADMIN_USERNAME, JWT_EXPIRE_HOURS, JWT_SECRET
from app.database import get_db


def generate_api_key() -> str:
    return secrets.token_hex(16)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def create_admin_token() -> str:
    payload = {"sub": ADMIN_USERNAME, "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)}
    return encode(payload, JWT_SECRET, algorithm="HS256")


def verify_admin_token(token: str) -> bool:
    try:
        payload = decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub") == ADMIN_USERNAME
    except InvalidTokenError:
        return False


def authenticate_developer(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> models.Developer:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid api key")
    key = authorization[7:].strip()
    if not key:
        raise HTTPException(status_code=401, detail="invalid api key")
    developer = db.query(models.Developer).filter(
        models.Developer.api_key_hash == hash_api_key(key)
    ).first()
    if developer is None or developer.status != "active":
        raise HTTPException(status_code=401, detail="invalid api key")
    return developer


def require_admin(
    authorization: str = Header(default=""),
) -> None:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="admin authentication required")
    token = authorization[7:].strip()
    if not verify_admin_token(token):
        raise HTTPException(status_code=401, detail="admin authentication required")
