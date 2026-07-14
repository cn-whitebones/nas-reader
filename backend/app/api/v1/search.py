"""搜索路由:按文件名 + 元数据(标题/作者/标签/描述)搜索。

用 SQLite LIKE(小写归一)做包含匹配;受权限过滤。作者/标签为 JSON 数组,
序列化为文本后整体模糊匹配,个人库量级足够。
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, BookFormat, BookMetadata, BookStatus
from app.models.user import User
from app.schemas.auth import Page
from app.schemas.book import BookBrief
from app.services.permission import apply_book_filter, get_readable_source_map

router = APIRouter(tags=["search"])


def _ci_like(col, like: str):
    """大小写不敏感的包含匹配(SQLite 无 ILIKE,用 lower 归一)。"""
    return func.lower(col).like(like.lower())


@router.get("/search", response_model=Page[BookBrief])
async def search(
    q: str = Query(min_length=1, max_length=200),
    format: BookFormat | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source_map = await get_readable_source_map(db, user)
    like = f"%{q}%"

    base = (
        select(Book)
        .outerjoin(BookMetadata, BookMetadata.book_id == Book.id)
        .where(Book.status == BookStatus.active)
        .where(
            or_(
                _ci_like(Book.file_name, like),
                _ci_like(BookMetadata.title, like),
                _ci_like(BookMetadata.description, like),
                _ci_like(BookMetadata.publisher, like),
                # 作者/标签为 JSON 数组:序列化为文本后整体模糊匹配
                _ci_like(cast(BookMetadata.authors, String), like),
                _ci_like(cast(BookMetadata.tags, String), like),
            )
        )
        .options(selectinload(Book.book_metadata))
    )
    base = apply_book_filter(base, user, source_map)
    if format:
        base = base.where(Book.format == format)

    total = await db.scalar(select(func.count()).select_from(base.order_by(None).subquery())) or 0
    result = await db.execute(base.order_by(Book.file_name).offset((page - 1) * size).limit(size))

    from app.api.v1.books import _brief

    items = [_brief(b) for b in result.scalars().all()]
    return Page(items=items, total=total, page=page, size=size)
