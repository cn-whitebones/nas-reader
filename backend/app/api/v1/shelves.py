"""书架路由:单书架模式。每个用户仅有一个默认书架,创建用户时预建。

历史遗留可能存在多个书架,这里始终取该用户最早创建的书架作为默认书架;
若不存在则惰性创建。对外只暴露"我的书架"及其收藏操作。
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, BookStatus
from app.models.reading import Shelf, ShelfBook
from app.models.user import User
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
    shelf = await get_or_create_default_shelf(db, user.id)
    result = await db.execute(
        select(Book)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .where(ShelfBook.shelf_id == shelf.id, Book.status == BookStatus.active)
        .options(selectinload(Book.book_metadata))
        .order_by(ShelfBook.added_at.desc())
    )
    from app.api.v1.books import _brief

    return [_brief(b) for b in result.scalars().all()]


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
