from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.config import ADMIN_PASSWORD, ADMIN_USERNAME
from app.core.security import create_admin_token, require_admin
from app.database import get_db
from app.models import ApiCallLog, Developer
from app.schemas import AdminLogin, AdminToken, DeveloperOut, DeveloperUpdate, StatOut

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])


@router.post("/login", response_model=AdminToken)
def login(payload: AdminLogin):
    if payload.username != ADMIN_USERNAME or payload.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="invalid credentials")
    return AdminToken(token=create_admin_token())


@router.get("/developers", response_model=list[DeveloperOut], dependencies=[Depends(require_admin)])
def list_developers(db: Session = Depends(get_db)):
    return db.query(Developer).order_by(Developer.id).all()


@router.put("/developers/{developer_id}", response_model=DeveloperOut, dependencies=[Depends(require_admin)])
def update_developer(developer_id: int, payload: DeveloperUpdate, db: Session = Depends(get_db)):
    developer = db.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(status_code=404, detail="developer not found")
    if payload.status is not None:
        if payload.status not in ("active", "disabled"):
            raise HTTPException(status_code=400, detail="invalid status")
        developer.status = payload.status
    if payload.quota_limit is not None:
        if payload.quota_limit < 0:
            raise HTTPException(status_code=400, detail="invalid quota limit")
        developer.quota_limit = payload.quota_limit
    db.commit()
    db.refresh(developer)
    return developer


@router.get("/stats", response_model=list[StatOut], dependencies=[Depends(require_admin)])
def get_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(
            ApiCallLog.endpoint,
            func.count(ApiCallLog.id).label("count"),
            func.sum(case((ApiCallLog.status_code < 400, 1), else_=0)).label("success"),
            func.sum(case((ApiCallLog.status_code >= 400, 1), else_=0)).label("failed"),
        )
        .group_by(ApiCallLog.endpoint)
        .all()
    )
    return [
        StatOut(endpoint=endpoint, count=count, success=success or 0, failed=failed or 0)
        for endpoint, count, success, failed in rows
    ]
