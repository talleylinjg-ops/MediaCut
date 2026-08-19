from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import billing
from app.core.security import (
    authenticate_client,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
    create_client_token,
)
from app.database import get_db
from app.models import ApiCallLog, Developer
from app.schemas import (
    ApiKeyResponse,
    ClientLogin,
    ClientOut,
    ClientToken,
    DeveloperRegister,
    LogOut,
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
    developer = db.query(Developer).filter(Developer.email == payload.email.strip()).first()
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


@router.post("/client/reset-key", response_model=ApiKeyResponse)
def client_reset_key(developer: Developer = Depends(authenticate_client), db: Session = Depends(get_db)):
    api_key = generate_api_key()
    developer.api_key_hash = hash_api_key(api_key)
    db.commit()
    return ApiKeyResponse(developer_id=developer.id, api_key=api_key)
