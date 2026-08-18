from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


def check_quota(db: Session, developer: models.Developer) -> None:
    if developer.quota_date != date.today():
        developer.quota_date = date.today()
        developer.quota_used = 0
        db.commit()
        db.refresh(developer)
    if developer.quota_used >= developer.quota_limit:
        raise HTTPException(status_code=429, detail="quota exceeded")


def consume_quota(db: Session, developer: models.Developer) -> None:
    check_quota(db, developer)
    developer.quota_used += 1
    db.commit()
    db.refresh(developer)


def remaining_quota(developer: models.Developer) -> int:
    return max(0, developer.quota_limit - developer.quota_used)
