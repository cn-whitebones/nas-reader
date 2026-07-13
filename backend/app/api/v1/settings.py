"""系统设置路由:默认文件夹权限模板(仅管理员)。"""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.user import Permission
from app.schemas.auth import PermissionItem, PermissionUpdate

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_admin)])


@router.get("/default-permissions", response_model=list[PermissionItem])
async def get_default_permissions(db: AsyncSession = Depends(get_db)):
    """默认权限模板:user_id 为 NULL 的权限行,新建用户时据此初始化。"""
    result = await db.execute(select(Permission).where(Permission.user_id.is_(None)))
    return list(result.scalars().all())


@router.put("/default-permissions", response_model=list[PermissionItem])
async def set_default_permissions(payload: PermissionUpdate, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Permission).where(Permission.user_id.is_(None)))
    for item in payload.permissions:
        db.add(
            Permission(
                user_id=None,
                source_id=item.source_id,
                sub_path=item.sub_path,
                can_read=item.can_read,
            )
        )
    await db.commit()
    result = await db.execute(select(Permission).where(Permission.user_id.is_(None)))
    return list(result.scalars().all())
