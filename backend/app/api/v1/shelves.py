"""书架路由:书架 CRUD、收藏/取消收藏、书架内图书列表。每用户独立。"""
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
from app.schemas.book import BookBrief, ShelfBookAdd, ShelfCreate, ShelfOut, ShelfUpdate
from app.services.permission import can_read_book

router = APIRouter(prefix="/shelves", tags=["shelves"])


async def _get_own_shelf(db: AsyncSession, user: User, shelf_id: uuid.UUID) -> Shelf:
    shelf = await db.get(Shelf, shelf_id)
    if shelf is None or shelf.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书架不存在")
    return shelf


@router.get("", response_model=list[ShelfOut])
async def list_shelves(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Shelf, func.count(ShelfBook.book_id))
        .outerjoin(ShelfBook, ShelfBook.shelf_id == Shelf.id)
        .where(Shelf.user_id == user.id)
        .group_by(Shelf.id)
        .order_by(Shelf.sort_order, Shelf.created_at)
    )
    return [
        ShelfOut(
            id=s.id, name=s.name, sort_order=s.sort_order, book_count=cnt, created_at=s.created_at
        )
        for s, cnt in result.all()
    ]


@router.post("", response_model=ShelfOut, status_code=status.HTTP_201_CREATED)
async def create_shelf(
    payload: ShelfCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    exists = await db.scalar(
        select(Shelf.id).where(Shelf.user_id == user.id, Shelf.name == payload.name)
    )
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="同名书架已存在")
    shelf = Shelf(user_id=user.id, name=payload.name, sort_order=payload.sort_order)
    db.add(shelf)
    await db.commit()
    await db.refresh(shelf)
    return ShelfOut(
        id=shelf.id, name=shelf.name, sort_order=shelf.sort_order, book_count=0,
        created_at=shelf.created_at,
    )


@router.patch("/{shelf_id}", response_model=ShelfOut)
async def update_shelf(
    shelf_id: uuid.UUID,
    payload: ShelfUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    shelf = await _get_own_shelf(db, user, shelf_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(shelf, key, value)
    await db.commit()
    await db.refresh(shelf)
    cnt = await db.scalar(select(func.count()).select_from(ShelfBook).where(ShelfBook.shelf_id == shelf_id))
    return ShelfOut(
        id=shelf.id, name=shelf.name, sort_order=shelf.sort_order, book_count=cnt or 0,
        created_at=shelf.created_at,
    )


@router.delete("/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(
    shelf_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    shelf = await _get_own_shelf(db, user, shelf_id)
    await db.delete(shelf)
    await db.commit()


@router.get("/{shelf_id}/books", response_model=list[BookBrief])
async def shelf_books(
    shelf_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_own_shelf(db, user, shelf_id)
    result = await db.execute(
        select(Book)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .where(ShelfBook.shelf_id == shelf_id)
        .options(selectinload(Book.book_metadata))
        .order_by(ShelfBook.added_at.desc())
    )
    from app.api.v1.books import _brief

    return [_brief(b) for b in result.scalars().all()]


@router.post("/{shelf_id}/books", status_code=status.HTTP_204_NO_CONTENT)
async def add_to_shelf(
    shelf_id: uuid.UUID,
    payload: ShelfBookAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_own_shelf(db, user, shelf_id)
    book = await db.get(Book, payload.book_id)
    if book is None or book.status != BookStatus.active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图书不存在")
    if not await can_read_book(db, user, book):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权收藏该图书")
    exists = await db.get(ShelfBook, {"shelf_id": shelf_id, "book_id": payload.book_id})
    if exists is None:
        db.add(ShelfBook(shelf_id=shelf_id, book_id=payload.book_id))
        await db.commit()


@router.delete("/{shelf_id}/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_shelf(
    shelf_id: uuid.UUID,
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_own_shelf(db, user, shelf_id)
    link = await db.get(ShelfBook, {"shelf_id": shelf_id, "book_id": book_id})
    if link is not None:
        await db.delete(link)
        await db.commit()
