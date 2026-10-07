#!/usr/bin/env python3
"""Seed SAAS 开发者账号（幂等）：didi AI 站点对接使用的 internal 渠道账号。

用法（需先加载 .env 环境变量）：
    python3 scripts/seed_saas.py

行为：
    - 按 email 查找 saas@didimedia.com；存在则更新 Key 与配额，不存在则创建
    - Key 以 sha256 哈希写入 api_key_hash，明文写入 api_key 字段（便于后台核对）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_api_key
from app.database import Base, SessionLocal, engine
from app import models

SAAS_EMAIL = "saas@didimedia.com"
SAAS_NAME = "SAAS didi AI"
SAAS_KEY = os.environ.get("SAAS_API_KEY", "b0a27d1311dfc65850393e6c88bb177e")
SAAS_QUOTA = int(os.environ.get("SAAS_QUOTA_LIMIT", "100000"))


def main() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        dev = db.query(models.Developer).filter(models.Developer.email == SAAS_EMAIL).first()
        if dev:
            changed = []
            if dev.api_key_hash != hash_api_key(SAAS_KEY):
                dev.api_key_hash = hash_api_key(SAAS_KEY)
                dev.api_key = SAAS_KEY
                changed.append("api_key")
            if dev.billing_type != "internal":
                dev.billing_type = "internal"
                changed.append("billing_type")
            if dev.quota_limit != SAAS_QUOTA:
                dev.quota_limit = SAAS_QUOTA
                changed.append("quota_limit")
            if dev.status != "active":
                dev.status = "active"
                changed.append("status")
            if changed:
                db.commit()
                print(f"updated developer id={dev.id} fields={','.join(changed)}")
            else:
                print(f"developer id={dev.id} already up to date")
        else:
            dev = models.Developer(
                name=SAAS_NAME,
                email=SAAS_EMAIL,
                password_hash="",
                api_key_hash=hash_api_key(SAAS_KEY),
                api_key=SAAS_KEY,
                billing_type="internal",
                balance=0,
                status="active",
                quota_limit=SAAS_QUOTA,
            )
            db.add(dev)
            db.commit()
            db.refresh(dev)
            print(f"created developer id={dev.id} email={SAAS_EMAIL}")
        print("seed_saas: OK")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
