import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Developer, RechargeOrder
from app.services import payment_service

router = APIRouter(prefix="/api/v1/pay", tags=["支付回调"])


def _settle_order(db: Session, order_no: str) -> RechargeOrder | None:
    order = db.query(RechargeOrder).filter(RechargeOrder.order_no == order_no).first()
    if order is None:
        return None
    if order.status == "paid":
        return order
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    developer = db.get(Developer, order.developer_id)
    if developer is not None:
        developer.balance += order.points
    db.commit()
    return order


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    data = {k: v for k, v in form.items()}
    if not payment_service.verify_alipay_notify(data):
        raise HTTPException(status_code=400, detail="sign verify failed")
    if data.get("trade_status") not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return {"code": "success", "msg": "ignored"}
    order = _settle_order(db, data.get("out_trade_no", ""))
    if order is None:
        return {"code": "fail", "msg": "order not found"}
    return {"code": "success", "msg": "ok"}


@router.post("/wechat/notify")
async def wechat_notify(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        resource = body["resource"]
        data = payment_service.decrypt_wechat_notify(
            resource["ciphertext"], resource["nonce"], resource["associated_data"]
        )
    except (KeyError, payment_service.PayNotConfigured, Exception):
        raise HTTPException(status_code=400, detail="invalid notify")

    if data.get("trade_state") != "SUCCESS":
        return {"code": "SUCCESS", "message": "ignored"}
    order = _settle_order(db, data.get("out_trade_no", ""))
    if order is None:
        return {"code": "FAIL", "message": "order not found"}
    return {"code": "SUCCESS", "message": "ok"}
