"""认证与首次启动引导路由。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, has_any_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.reading import ReadingSettings
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    RefreshRequest,
    SetupRequest,
    SetupStatus,
    TokenResponse,
    UserOut,
)

router = APIRouter(tags=["auth"])


@router.get("/auth/setup-status", response_model=SetupStatus)
async def setup_status(db: AsyncSession = Depends(get_db)):
    """前端启动时调用:是否需要显示引导页(尚无任何用户)。"""
    return SetupStatus(needs_setup=not await has_any_user(db))


@router.post("/auth/setup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def setup_admin(payload: SetupRequest, db: AsyncSession = Depends(get_db)):
    """首次启动引导:创建首个管理员。已存在用户则拒绝。"""
    if await has_any_user(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="系统已初始化")
    admin = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.admin,
    )
    db.add(admin)
    await db.flush()
    db.add(ReadingSettings(user_id=admin.id))
    await db.commit()
    await db.refresh(admin)
    return admin


@router.post("/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    sub = str(user.id)
    return TokenResponse(
        access_token=create_access_token(sub), refresh_token=create_refresh_token(sub)
    )


@router.post("/auth/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌")
    sub = data.get("sub")
    user = await db.get(User, uuid.UUID(sub)) if sub else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return AccessTokenResponse(access_token=create_access_token(sub))


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
