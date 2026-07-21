"""权限管理共享服务:批量替换权限配置等通用逻辑。"""
import uuid
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Permission
from app.schemas.auth import PermissionItem


async def replace_permissions(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    permissions: list[PermissionItem],
) -> list[Permission]:
    """替换指定用户(或默认模板user_id=None)的全部权限配置。

    流程:
    1. 删除该用户所有现有权限
    2. 批量插入新权限
    3. 提交并返回更新后的权限列表

    Args:
        db: 数据库会话
        user_id: 用户ID, None 表示默认权限模板
        permissions: 新权限列表

    Returns:
        更新后的权限列表
    """
    # 删除现有权限
    await db.execute(delete(Permission).where(Permission.user_id == user_id))
    # 插入新权限
    for item in permissions:
        db.add(
            Permission(
                user_id=user_id,
                source_id=item.source_id,
                sub_path=item.sub_path,
                can_read=item.can_read,
            )
        )
    await db.commit()
    # 返回更新后的列表
    result = await db.execute(select(Permission).where(Permission.user_id == user_id))
    return list(result.scalars().all())
