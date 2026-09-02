from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.core import billing


def check_quota(db: Session, developer: models.Developer, price: int = 0) -> None:
    if developer.quota_date != date.today():
        developer.quota_date = date.today()
        developer.quota_used = 0
        db.commit()
        db.refresh(developer)
    if developer.quota_used >= developer.quota_limit:
        raise HTTPException(status_code=429, detail="quota exceeded")
    if developer.billing_type == billing.BILLING_EXTERNAL and price > 0 and developer.balance < price:
        raise HTTPException(
            status_code=402,
            detail=f"余额不足（当前 {developer.balance} 点，本次需 {price} 点）。请在客户控制台充值或联系管理员。",
        )


def consume_quota(db: Session, developer: models.Developer, price: int = 0) -> None:
    check_quota(db, developer, price)
    developer.quota_used += 1
    if developer.billing_type == billing.BILLING_EXTERNAL and price > 0:
        developer.balance -= price
    db.commit()
    db.refresh(developer)


def remaining_quota(developer: models.Developer) -> int:
    return max(0, developer.quota_limit - developer.quota_used)
