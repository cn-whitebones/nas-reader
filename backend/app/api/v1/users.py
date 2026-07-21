"""用户管理与权限授权路由(仅管理员)。"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.reading import ReadingSettings
from app.models.user import Permission, User
from app.schemas.auth import (
    Page,
    PermissionItem,
    PermissionUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.book_query import paginate_query
from app.services.shelf import get_or_create_default_shelf

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_current_admin)])


async def _copy_default_permissions(db: AsyncSession, user_id: uuid.UUID) -> None:
    """将默认权限模板(user_id 为 NULL)复制给新用户。"""
    result = await db.execute(select(Permission).where(Permission.user_id.is_(None)))
    for tpl in result.scalars().all():
        db.add(
            Permission(
                user_id=user_id,
                source_id=tpl.source_id,
                sub_path=tpl.sub_path,
                can_read=tpl.can_read,
            )
        )


@router.get("", response_model=Page[UserOut])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).order_by(User.created_at.desc())
    total, items = await paginate_query(stmt, page, size, db)
    return Page(items=items, total=total, page=page, size=size)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(User.id).where(User.username == payload.username))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    db.add(ReadingSettings(user_id=user.id))
    await _copy_default_permissions(db, user.id)
    await db.commit()
    await get_or_create_default_shelf(db, user.id)
    await db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: uuid.UUID, payload: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    await db.delete(user)
    await db.commit()


@router.get("/{user_id}/permissions", response_model=list[PermissionItem])
async def get_user_permissions(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Permission).where(Permission.user_id == user_id))
    return list(result.scalars().all())


@router.put("/{user_id}/permissions", response_model=list[PermissionItem])
async def set_user_permissions(
    user_id: uuid.UUID, payload: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    from app.services.permission_service import replace_permissions
    return await replace_permissions(db, user_id, payload.permissions)
