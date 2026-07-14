"""书架服务:默认书架的获取/创建。单书架模式的核心逻辑。"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading import Shelf

DEFAULT_SHELF_NAME = "我的收藏"


async def get_or_create_default_shelf(db: AsyncSession, user_id: uuid.UUID) -> Shelf:
    """返回用户的默认书架:取最早创建的一个;不存在则创建。

    历史数据可能有多个书架,始终以最早创建的作为默认书架,保证幂等。
    """
    shelf = await db.scalar(
        select(Shelf)
        .where(Shelf.user_id == user_id)
        .order_by(Shelf.created_at, Shelf.sort_order)
        .limit(1)
    )
    if shelf is None:
        shelf = Shelf(user_id=user_id, name=DEFAULT_SHELF_NAME, sort_order=0)
        db.add(shelf)
        await db.commit()
        await db.refresh(shelf)
    return shelf
