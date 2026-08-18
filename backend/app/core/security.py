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


def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    calc = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return secrets.compare_digest(calc, digest)


def create_admin_token() -> str:
    payload = {"sub": ADMIN_USERNAME, "role": "admin", "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)}
    return encode(payload, JWT_SECRET, algorithm="HS256")


def create_client_token(developer_id: int) -> str:
    payload = {
        "sub": str(developer_id),
        "role": "client",
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return encode(payload, JWT_SECRET, algorithm="HS256")


def _decode_token(token: str) -> dict:
    try:
        return decode(token, JWT_SECRET, algorithms=["HS256"])
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="authentication required")


def verify_admin_token(token: str) -> bool:
    try:
        payload = _decode_token(token)
        return payload.get("role") == "admin" and payload.get("sub") == ADMIN_USERNAME
    except HTTPException:
        return False


def authenticate_client(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> models.Developer:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="authentication required")
    token = authorization[7:].strip()
    payload = _decode_token(token)
    if payload.get("role") != "client":
        raise HTTPException(status_code=401, detail="authentication required")
    developer = db.get(models.Developer, int(payload["sub"]))
    if developer is None or developer.status != "active":
        raise HTTPException(status_code=401, detail="authentication required")
    return developer


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
