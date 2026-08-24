import uuid
from datetime import date, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Date

from app.database import Base


def gen_task_id():
    return uuid.uuid4().hex


class Developer(Base):
    __tablename__ = "developer"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(256), nullable=False)
    password_hash = Column(String(256), default="", nullable=False)
    api_key_hash = Column(String(256), unique=True, nullable=False)
    billing_type = Column(String(16), default="external", nullable=False)
    balance = Column(Integer, default=0, nullable=False)
    status = Column(String(16), default="active", nullable=False)
    quota_limit = Column(Integer, default=1000, nullable=False)
    quota_used = Column(Integer, default=0, nullable=False)
    quota_date = Column(Date, default=date.today, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(32), unique=True, index=True, nullable=False, default=gen_task_id)
    developer_id = Column(Integer, ForeignKey("developer.id"), nullable=False, index=True)
    task_type = Column(String(32), nullable=False)
    status = Column(String(16), default="pending", nullable=False)
    params = Column(Text, default="{}", nullable=False)
    result_url = Column(String(512))
    result_text = Column(Text)
    result_kind = Column(String(16))
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ApiCallLog(Base):
    __tablename__ = "api_call_log"

    id = Column(Integer, primary_key=True, index=True)
    developer_id = Column(Integer, ForeignKey("developer.id"), nullable=False, index=True)
    endpoint = Column(String(256), nullable=False)
    status_code = Column(Integer, nullable=False)
    cost = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AppConfig(Base):
    __tablename__ = "app_config"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)


class RechargeOrder(Base):
    __tablename__ = "recharge_order"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(32), unique=True, index=True, nullable=False)
    developer_id = Column(Integer, ForeignKey("developer.id"), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    points = Column(Integer, nullable=False, default=0)
    payment_provider = Column(String(16), nullable=False, default="alipay")
    qr_content = Column(Text)
    status = Column(String(16), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_at = Column(DateTime)
