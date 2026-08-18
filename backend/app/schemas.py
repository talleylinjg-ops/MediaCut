from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DeveloperRegister(BaseModel):
    name: str
    email: str


class ApiKeyResponse(BaseModel):
    developer_id: int
    api_key: str


class DeveloperOut(BaseModel):
    id: int
    name: str
    email: str
    api_key_hash: str
    status: str
    quota_limit: int
    quota_used: int
    quota_date: date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeveloperUpdate(BaseModel):
    status: Optional[str] = None
    quota_limit: Optional[int] = None


class TaskOut(BaseModel):
    task_id: str
    task_type: str
    status: str
    result_url: Optional[str] = None
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


class StatOut(BaseModel):
    endpoint: str
    count: int
    success: int
    failed: int
