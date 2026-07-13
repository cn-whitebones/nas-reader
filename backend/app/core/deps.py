"""FastAPI 依赖:当前用户、管理员校验。"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="无效或过期的令牌",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise _credentials_exc
    sub = payload.get("sub")
    if not sub:
        raise _credentials_exc
    user = await db.get(User, uuid.UUID(sub))
    if user is None or not user.is_active:
        raise _credentials_exc
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


async def has_any_user(db: AsyncSession) -> bool:
    """是否已存在任意用户(用于首次启动引导判断)。"""
    result = await db.execute(select(User.id).limit(1))
    return result.first() is not None
