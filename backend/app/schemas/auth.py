"""Pydantic schemas:认证、用户、通用响应。"""
import uuid
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- 用户 ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.user


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    """当前用户修改自己的密码,需校验旧密码。"""

    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class SetupRequest(BaseModel):
    """首次启动引导:创建首个管理员。"""

    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class SetupStatus(BaseModel):
    needs_setup: bool


# ---------- 权限 ----------
class PermissionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_id: uuid.UUID
    sub_path: str | None = None
    can_read: bool = True


class PermissionUpdate(BaseModel):
    permissions: list[PermissionItem]
