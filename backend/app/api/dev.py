import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import billing
from app.core.security import (
    admin_password_matches,
    authenticate_client,
    authenticate_developer,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
    create_client_token,
)
from app.database import get_db
from app.models import ApiCallLog, Developer, RechargeOrder
from app.schemas import (
    ApiKeyResponse,
    ClientLogin,
    ClientOut,
    ClientPasswordChange,
    ClientToken,
    DeveloperRegister,
    KeyInfoOut,
    LogOut,
    RechargeOrderCreate,
    RechargeOrderOut,
    RechargePayResponse,
    RechargeRequest,
    RechargeResponse,
)

router = APIRouter(prefix="/api/v1/dev", tags=["开发者"])


@router.post("/register", response_model=ApiKeyResponse)
def register(payload: DeveloperRegister, db: Session = Depends(get_db)):
    if not payload.name.strip() or not payload.email.strip():
        raise HTTPException(status_code=400, detail="name and email are required")
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="password must be at least 6 characters")
    if db.query(Developer).filter(Developer.email == payload.email.strip()).first():
        raise HTTPException(status_code=409, detail="email already registered")
    api_key = generate_api_key()
    developer = Developer(
        name=payload.name.strip(),
        email=payload.email.strip(),
        password_hash=hash_password(payload.password),
        api_key_hash=hash_api_key(api_key),
        billing_type=billing.BILLING_EXTERNAL,
        balance=billing.SIGNUP_BONUS,
    )
    db.add(developer)
    db.commit()
    db.refresh(developer)
    return ApiKeyResponse(developer_id=developer.id, api_key=api_key)


@router.post("/client/login", response_model=ClientToken)
def client_login(payload: ClientLogin, db: Session = Depends(get_db)):
    email = payload.email.strip()
    developer = db.query(Developer).filter(Developer.email == email).first()

    if email and admin_password_matches(payload.password) and email.lower() == "admin":
        if developer is None:
            api_key = generate_api_key()
            developer = Developer(
                name="admin",
                email="admin",
                password_hash=hash_password(payload.password),
                api_key_hash=hash_api_key(api_key),
                billing_type=billing.BILLING_EXTERNAL,
                balance=billing.SIGNUP_BONUS,
            )
            db.add(developer)
            db.commit()
            db.refresh(developer)
        return ClientToken(token=create_client_token(developer.id))

    if developer is None or not verify_password(payload.password, developer.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    if developer.status != "active":
        raise HTTPException(status_code=403, detail="account disabled")
    return ClientToken(token=create_client_token(developer.id))


@router.get("/client/me", response_model=ClientOut)
def client_me(developer: Developer = Depends(authenticate_client)):
    return developer


@router.get("/client/logs", response_model=list[LogOut])
def client_logs(developer: Developer = Depends(authenticate_client), db: Session = Depends(get_db)):
    return (
        db.query(ApiCallLog)
        .filter(ApiCallLog.developer_id == developer.id)
        .order_by(ApiCallLog.id.desc())
        .limit(50)
        .all()
    )


@router.post("/client/recharge", response_model=RechargeResponse)
def client_recharge(
    payload: RechargeRequest,
    developer: Developer = Depends(authenticate_client),
    db: Session = Depends(get_db),
):
    if payload.amount < 1 or payload.amount > 1000000:
        raise HTTPException(status_code=400, detail="invalid amount")
    developer.balance += payload.amount
    db.commit()
    db.refresh(developer)
    return RechargeResponse(balance=developer.balance)


@router.get("/key/info", response_model=KeyInfoOut)
def key_info(developer: Developer = Depends(authenticate_developer)):
    return developer


@router.post("/client/password")
def client_change_password(
    payload: ClientPasswordChange,
    developer: Developer = Depends(authenticate_client),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, developer.password_hash):
        raise HTTPException(status_code=401, detail="current password incorrect")
    if not payload.new_password or len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="new password must be at least 6 characters")
    developer.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}


@router.post("/client/recharge/order", response_model=RechargeOrderOut)
def create_recharge_order(
    payload: RechargeOrderCreate,
    developer: Developer = Depends(authenticate_client),
    db: Session = Depends(get_db),
):
    if payload.amount < 1 or payload.amount > 1000000:
        raise HTTPException(status_code=400, detail="invalid amount")
    if payload.payment_method not in ("alipay", "wechat"):
        raise HTTPException(status_code=400, detail="invalid payment method")
    order = RechargeOrder(
        order_no=secrets.token_hex(8).upper(),
        developer_id=developer.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        status="pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/client/recharge/order/{order_no}/pay", response_model=RechargePayResponse)
def pay_recharge_order(
    order_no: str,
    developer: Developer = Depends(authenticate_client),
    db: Session = Depends(get_db),
):
    order = (
        db.query(RechargeOrder)
        .filter(RechargeOrder.order_no == order_no, RechargeOrder.developer_id == developer.id)
        .first()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.status == "paid":
        raise HTTPException(status_code=400, detail="order already paid")
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    developer.balance += order.amount
    db.commit()
    return RechargePayResponse(order_no=order.order_no, status="paid", balance=developer.balance)


@router.get("/client/recharge/orders", response_model=list[RechargeOrderOut])
def list_recharge_orders(
    developer: Developer = Depends(authenticate_client),
    db: Session = Depends(get_db),
):
    return (
        db.query(RechargeOrder)
        .filter(RechargeOrder.developer_id == developer.id)
        .order_by(RechargeOrder.id.desc())
        .limit(20)
        .all()
    )


@router.post("/client/reset-key", response_model=ApiKeyResponse)
def client_reset_key(developer: Developer = Depends(authenticate_client), db: Session = Depends(get_db)):
    api_key = generate_api_key()
    developer.api_key_hash = hash_api_key(api_key)
    db.commit()
    return ApiKeyResponse(developer_id=developer.id, api_key=api_key)
