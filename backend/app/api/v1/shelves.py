"""书架路由:单书架模式。每个用户仅有一个默认书架,创建用户时预建。

历史遗留可能存在多个书架,这里始终取该用户最早创建的书架作为默认书架;
若不存在则惰性创建。对外只暴露"我的书架"及其收藏操作。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, BookStatus
from app.models.reading import Shelf, ShelfBook
from app.models.user import User
from app.schemas.auth import Page
from app.schemas.book import BookBrief, ShelfBookAdd, ShelfOut
from app.services.permission import can_read_book
from app.services.shelf import get_or_create_default_shelf

router = APIRouter(prefix="/shelves", tags=["shelves"])


@router.get("/my", response_model=ShelfOut)
async def my_shelf(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """获取当前用户的默认书架(含收藏数)。"""
    shelf = await get_or_create_default_shelf(db, user.id)
    cnt = await db.scalar(
        select(func.count()).select_from(ShelfBook).where(ShelfBook.shelf_id == shelf.id)
    )
    return ShelfOut(
        id=shelf.id, name=shelf.name, sort_order=shelf.sort_order, book_count=cnt or 0,
        created_at=shelf.created_at,
    )


@router.get("/my/books", response_model=list[BookBrief])
async def my_shelf_books(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """兼容旧版本:返回全部收藏(不推荐)。新前端用分页端点 /my/books/paged."""
    shelf = await get_or_create_default_shelf(db, user.id)
    result = await db.execute(
        select(Book)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .where(ShelfBook.shelf_id == shelf.id, Book.status == BookStatus.active)
        .options(selectinload(Book.book_metadata))
        .order_by(ShelfBook.added_at.desc())
    )

    return [BookBrief.from_model(b) for b in result.scalars().all()]


@router.get("/my/books/paged", response_model=Page[BookBrief])
async def my_shelf_books_paged(
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
    sort: str = Query("shelf_added", pattern="^(title|author|words|chapters|added|size|shelf_added)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页获取收藏列表,支持搜索和排序,与书库接口一致。"""
    from app.models.book import BookMetadata
    from app.services.permission import apply_book_filter
    from app.services.permission import get_readable_source_map

    shelf = await get_or_create_default_shelf(db, user.id)
    source_map = await get_readable_source_map(db, user)
    # outerjoin 元数据用于排序/筛选
    base = (
        select(Book)
        .outerjoin(BookMetadata, BookMetadata.book_id == Book.id)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .where(ShelfBook.shelf_id == shelf.id, Book.status == BookStatus.active)
        .options(selectinload(Book.book_metadata))
    )
    base = apply_book_filter(base, user, source_map)
    # 关键字模糊匹配，与 books.py 一致
    if q and q.strip():
        like = f"%{q.strip()}%"
        from sqlalchemy import String, cast, or_

        base = base.where(
            or_(
                func.lower(Book.file_name).like(like.lower()),
                func.lower(BookMetadata.title).like(like.lower()),
                func.lower(BookMetadata.description).like(like.lower()),
                func.lower(BookMetadata.publisher).like(like.lower()),
                func.lower(cast(BookMetadata.authors, String)).like(like.lower()),
                func.lower(cast(BookMetadata.tags, String)).like(like.lower()),
            )
        )
    count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
    total = await db.scalar(count_stmt) or 0

    def _d(col):
        return col.desc() if order == "desc" else col.asc()

    # 排序与书库一致:nulls last
    if sort == "author":
        primary = _d(BookMetadata.author_sort)
    elif sort == "words":
        primary = _d(Book.word_count)
    elif sort == "chapters":
        primary = _d(Book.chapter_count)
    elif sort == "added":
        primary = _d(Book.added_at)
    elif sort == "size":
        primary = _d(Book.file_size)
    elif sort == "shelf_added":
        primary = _d(ShelfBook.added_at)
    else:  # title
        primary = _d(BookMetadata.title_sort)
    ordered = base.order_by(primary, Book.dir_path.asc(), Book.file_name.asc())
    result = await db.execute(ordered.offset((page - 1) * size).limit(size))
    items = [BookBrief.from_model(b) for b in result.scalars().all()]
    return Page(items=items, total=total, page=page, size=size)


@router.post("/my/books", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_my_shelf(
    payload: ShelfBookAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shelf = await get_or_create_default_shelf(db, user.id)
    book = await db.get(Book, payload.book_id)
    if book is None or book.status != BookStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图书不存在")
    if not await can_read_book(db, user, book):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权收藏该图书")
    exists = await db.get(ShelfBook, {"shelf_id": shelf.id, "book_id": payload.book_id})
    if exists is None:
        db.add(ShelfBook(shelf_id=shelf.id, book_id=payload.book_id))
        await db.commit()


@router.delete("/my/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_my_shelf(
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shelf = await get_or_create_default_shelf(db, user.id)
    link = await db.get(ShelfBook, {"shelf_id": shelf.id, "book_id": book_id})
    if link is not None:
        await db.delete(link)
        await db.commit()
