import base64
import json
import time
import uuid

import httpx

from app.core import settings

POINTS_PER_YUAN = 100
ALIPAY_GATEWAY = "https://openapi.alipay.com/gateway.do"
WECHAT_API = "https://api.mch.weixin.qq.com"


class PayNotConfigured(RuntimeError):
    pass


def _notify_url(provider: str) -> str:
    base = settings.get_pay_config("pay_notify_base").strip().rstrip("/")
    return f"{base}/api/v1/pay/{provider}/notify"


# ---------------- 支付宝当面付（扫码） ----------------

def _alipay_client():
    appid = settings.get_pay_config("pay_alipay_appid").strip()
    private_key = settings.get_pay_config("pay_alipay_private_key").strip()
    public_key = settings.get_pay_config("pay_alipay_public_key").strip()
    if not (appid and private_key and public_key):
        return None
    from alipay import AliPay

    return AliPay(
        appid=appid,
        app_notify_url=None,
        app_private_key_string=private_key,
        alipay_public_key_string=public_key,
        sign_type="RSA2",
    )


def create_alipay_qr(order_no: str, amount_yuan: float, subject: str) -> str:
    client = _alipay_client()
    if client is None:
        raise PayNotConfigured("支付宝支付渠道未配置")
    biz = client.api_alipay_trade_precreate(
        subject=subject,
        out_trade_no=order_no,
        total_amount=f"{amount_yuan:.2f}",
        notify_url=_notify_url("alipay"),
    )
    if not biz or biz.get("code") != "10000":
        raise RuntimeError(f"支付宝下单失败: {biz or 'no response'}")
    qr_code = biz.get("qr_code")
    if not qr_code:
        raise RuntimeError(f"支付宝未返回二维码: {biz}")
    return qr_code


def verify_alipay_notify(data: dict) -> bool:
    client = _alipay_client()
    if client is None:
        return False
    return client.verify(data)


# ---------------- 微信 Native 支付 ----------------

def _wechat_sign(message: str, private_key_pem: str) -> str:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    signature = key.sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def create_wechat_native(order_no: str, amount_yuan: float, description: str) -> str:
    appid = settings.get_pay_config("pay_wechat_appid").strip()
    mchid = settings.get_pay_config("pay_wechat_mchid").strip()
    apiv3_key = settings.get_pay_config("pay_wechat_apiv3_key").strip()
    serial = settings.get_pay_config("pay_wechat_serial_no").strip()
    private_key = settings.get_pay_config("pay_wechat_private_key").strip()
    if not all([appid, mchid, apiv3_key, serial, private_key]):
        raise PayNotConfigured("微信支付渠道未配置")

    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex
    path = "/v3/pay/transactions/native"
    body = json.dumps(
        {
            "appid": appid,
            "mchid": mchid,
            "description": description,
            "out_trade_no": order_no,
            "notify_url": _notify_url("wechat"),
            "amount": {"total": int(round(amount_yuan * 100)), "currency": "CNY"},
        },
        ensure_ascii=False,
    )
    message = f"POST\n{path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = _wechat_sign(message, private_key)
    auth = (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",'
        f'nonce_str="{nonce}",signature="{signature}",'
        f'timestamp="{timestamp}",serial_no="{serial}"'
    )
    resp = httpx.post(
        f"{WECHAT_API}{path}",
        content=body,
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        timeout=20,
    )
    data = resp.json()
    if "code_url" in data:
        return data["code_url"]
    raise RuntimeError(f"微信下单失败: {data.get('message', resp.text)}")


def decrypt_wechat_notify(ciphertext: str, nonce: str, associated_data: str) -> dict:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    apiv3_key = settings.get_pay_config("pay_wechat_apiv3_key").strip()
    if not apiv3_key:
        raise PayNotConfigured("微信 APIv3 密钥未配置")
    aesgcm = AESGCM(apiv3_key.encode())
    plaintext = aesgcm.decrypt(
        nonce.encode(),
        base64.b64decode(ciphertext),
        associated_data.encode(),
    )
    return json.loads(plaintext.decode())
