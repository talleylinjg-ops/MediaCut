from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeveloperRegister(BaseModel):
    name: str
    email: str
    password: str = ""


class ApiKeyResponse(BaseModel):
    developer_id: int
    api_key: str


class DeveloperOut(BaseModel):
    id: int
    name: str
    email: str
    api_key_hash: str
    billing_type: str
    balance: int
    status: str
    quota_limit: int
    quota_used: int
    quota_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeveloperUpdate(BaseModel):
    status: Optional[str] = None
    quota_limit: Optional[int] = None
    billing_type: Optional[str] = None
    recharge: Optional[int] = None


class TaskOut(BaseModel):
    task_id: str
    task_type: str
    status: str
    result_url: Optional[str] = None
    result_text: Optional[str] = None
    result_kind: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    status_url: str


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminToken(BaseModel):
    token: str


class AdminPasswordChange(BaseModel):
    current_password: str
    new_password: str


class ConfigOut(BaseModel):
    admin_username: str
    modelscope_configured: bool
    models: dict


class ConfigUpdate(BaseModel):
    modelscope_api_token: Optional[str] = None


class ClientLogin(BaseModel):
    email: str
    password: str


class ClientToken(BaseModel):
    token: str


class RechargeRequest(BaseModel):
    amount: int


class RechargeResponse(BaseModel):
    balance: int


class RechargeOrderCreate(BaseModel):
    amount: int
    payment_method: str = "alipay"


class RechargeOrderOut(BaseModel):
    order_no: str
    amount: int
    payment_method: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RechargePayResponse(BaseModel):
    order_no: str
    status: str
    balance: int


class ClientPasswordChange(BaseModel):
    current_password: str
    new_password: str


class KeyInfoOut(BaseModel):
    id: int
    name: str
    email: str
    billing_type: str
    balance: int

    model_config = ConfigDict(from_attributes=True)


class ClientOut(BaseModel):
    id: int
    name: str
    email: str
    billing_type: str
    balance: int
    quota_limit: int
    quota_used: int
    quota_date: date

    model_config = ConfigDict(from_attributes=True)


class LogOut(BaseModel):
    endpoint: str
    status_code: int
    cost: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StatOut(BaseModel):
    endpoint: str
    count: int
    success: int
    failed: int
    revenue: int


class DashboardOut(BaseModel):
    total_developers: int
    active_developers: int
    external_developers: int
    today_calls: int
    total_revenue: int
    pending_tasks: int
    total_balance: int
