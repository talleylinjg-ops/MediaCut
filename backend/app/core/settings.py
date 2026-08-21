from app import models
from app.config import MODELSCOPE_API_TOKEN as ENV_MODELSCOPE_TOKEN
from app.database import SessionLocal

ADMIN_PASSWORD_KEY = "admin_password_hash"
MODELSCOPE_TOKEN_KEY = "modelscope_api_token"


def _get_config(key: str) -> str:
    try:
        db = SessionLocal()
        try:
            row = db.get(models.AppConfig, key)
            if row is not None and row.value:
                return row.value
        finally:
            db.close()
    except Exception:
        pass
    return ""


def _set_config(key: str, value: str) -> None:
    db = SessionLocal()
    try:
        row = db.get(models.AppConfig, key)
        if row is None:
            db.add(models.AppConfig(key=key, value=value))
        else:
            row.value = value
        db.commit()
    finally:
        db.close()


def get_modelscope_token() -> str:
    stored = _get_config(MODELSCOPE_TOKEN_KEY)
    return stored or ENV_MODELSCOPE_TOKEN


def get_admin_password_hash() -> str:
    return _get_config(ADMIN_PASSWORD_KEY)


def set_admin_password_hash(value: str) -> None:
    _set_config(ADMIN_PASSWORD_KEY, value)


def set_modelscope_token(value: str) -> None:
    _set_config(MODELSCOPE_TOKEN_KEY, value)
