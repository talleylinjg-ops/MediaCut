from app import models
from app.config import MODELSCOPE_API_TOKEN as ENV_MODELSCOPE_TOKEN
from app.database import SessionLocal

ADMIN_PASSWORD_KEY = "admin_password_hash"
ADMIN_NAME_KEY = "admin_display_name"
MODELSCOPE_TOKEN_KEY = "modelscope_api_token"

PAY_CONFIG_KEYS = {
    "pay_alipay_appid": "支付宝 APPID",
    "pay_alipay_private_key": "支付宝应用私钥",
    "pay_alipay_public_key": "支付宝公钥",
    "pay_wechat_appid": "微信 AppID",
    "pay_wechat_mchid": "微信商户号",
    "pay_wechat_apiv3_key": "微信 APIv3 密钥",
    "pay_wechat_serial_no": "微信商户证书序列号",
    "pay_wechat_private_key": "微信商户证书私钥",
    "pay_notify_base": "支付回调基础地址",
}


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


def get_admin_display_name() -> str:
    return _get_config(ADMIN_NAME_KEY)


def set_admin_display_name(value: str) -> None:
    _set_config(ADMIN_NAME_KEY, value)


def set_modelscope_token(value: str) -> None:
    _set_config(MODELSCOPE_TOKEN_KEY, value)


def get_pay_config(key: str) -> str:
    return _get_config(key)


def set_pay_config(key: str, value: str) -> None:
    _set_config(key, value)
