from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.config import ADMIN_USERNAME, MODELSCOPE_MODELS
from app.core import settings
from app.core.security import (
    admin_password_matches,
    create_admin_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    require_admin,
)
from app.database import get_db
from app.models import ApiCallLog, Developer, Task
from app.schemas import (
    AdminLogin,
    AdminPasswordChange,
    AdminToken,
    ConfigOut,
    ConfigUpdate,
    DashboardOut,
    DeveloperOut,
    DeveloperUpdate,
    StatOut,
)

router = APIRouter(prefix="/api/v1/admin", tags=["管理后台"])


@router.post("/login", response_model=AdminToken)
def login(payload: AdminLogin):
    if payload.username != ADMIN_USERNAME or not admin_password_matches(payload.password):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return AdminToken(token=create_admin_token())


@router.put("/password", dependencies=[Depends(require_admin)])
def change_password(payload: AdminPasswordChange):
    if not admin_password_matches(payload.current_password):
        raise HTTPException(status_code=401, detail="current password incorrect")
    if not payload.new_password or len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")
    settings.set_admin_password_hash(hash_password(payload.new_password))
    return {"ok": True}


@router.get("/config", response_model=ConfigOut, dependencies=[Depends(require_admin)])
def get_config():
    return ConfigOut(
        admin_username=ADMIN_USERNAME,
        modelscope_configured=bool(settings.get_modelscope_token()),
        models=MODELSCOPE_MODELS,
        alipay_configured=bool(settings.get_pay_config("pay_alipay_appid")),
        wechat_configured=bool(settings.get_pay_config("pay_wechat_mchid")),
    )


@router.put("/config", dependencies=[Depends(require_admin)])
def update_config(payload: ConfigUpdate):
    if payload.modelscope_api_token is not None:
        token = payload.modelscope_api_token.strip()
        settings.set_modelscope_token(token)
    for key in settings.PAY_CONFIG_KEYS:
        value = getattr(payload, key, None)
        if value is not None:
            settings.set_pay_config(key, value.strip())
    return {"ok": True}


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


@router.post("/developers/{developer_id}/reset-key", response_model=DeveloperOut, dependencies=[Depends(require_admin)])
def admin_reset_key(developer_id: int, db: Session = Depends(get_db)):
    developer = db.get(Developer, developer_id)
    if developer is None:
        raise HTTPException(status_code=404, detail="developer not found")
    api_key = generate_api_key()
    developer.api_key_hash = hash_api_key(api_key)
    db.commit()
    db.refresh(developer)
    response = DeveloperOut.model_validate(developer)
    response.api_key_hash = f"KEY:{api_key}"
    return response


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
