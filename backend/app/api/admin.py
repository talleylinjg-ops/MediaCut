from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.config import ADMIN_PASSWORD, ADMIN_USERNAME
from app.core.security import create_admin_token, require_admin
from app.database import get_db
from app.models import ApiCallLog, Developer, Task
from app.schemas import AdminLogin, AdminToken, DashboardOut, DeveloperOut, DeveloperUpdate, StatOut

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
    if payload.billing_type is not None:
        if payload.billing_type not in ("internal", "external"):
            raise HTTPException(status_code=400, detail="invalid billing type")
        developer.billing_type = payload.billing_type
    if payload.recharge is not None:
        if payload.recharge < 0:
            raise HTTPException(status_code=400, detail="invalid recharge amount")
        developer.balance += payload.recharge
    db.commit()
    db.refresh(developer)
    return developer


@router.get("/dashboard", response_model=DashboardOut, dependencies=[Depends(require_admin)])
def get_dashboard(db: Session = Depends(get_db)):
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    total_developers = db.query(Developer).count()
    active_developers = db.query(Developer).filter(Developer.status == "active").count()
    external_developers = db.query(Developer).filter(Developer.billing_type == "external").count()
    today_calls = db.query(ApiCallLog).filter(ApiCallLog.created_at >= today_start).count()
    total_revenue = (
        db.query(func.sum(ApiCallLog.cost))
        .filter(ApiCallLog.status_code < 400)
        .scalar()
        or 0
    )
    pending_tasks = db.query(Task).filter(Task.status.in_(["pending", "running"])).count()
    total_balance = db.query(func.sum(Developer.balance)).scalar() or 0
    return DashboardOut(
        total_developers=total_developers,
        active_developers=active_developers,
        external_developers=external_developers,
        today_calls=today_calls,
        total_revenue=total_revenue,
        pending_tasks=pending_tasks,
        total_balance=total_balance,
    )


@router.get("/stats", response_model=list[StatOut], dependencies=[Depends(require_admin)])
def get_stats(db: Session = Depends(get_db)):
    rows = (
        db.query(
            ApiCallLog.endpoint,
            func.count(ApiCallLog.id).label("count"),
            func.sum(case((ApiCallLog.status_code < 400, 1), else_=0)).label("success"),
            func.sum(case((ApiCallLog.status_code >= 400, 1), else_=0)).label("failed"),
            func.sum(case((ApiCallLog.status_code < 400, ApiCallLog.cost), else_=0)).label("revenue"),
        )
        .group_by(ApiCallLog.endpoint)
        .all()
    )
    return [
        StatOut(endpoint=endpoint, count=count, success=success or 0, failed=failed or 0, revenue=revenue or 0)
        for endpoint, count, success, failed, revenue in rows
    ]
