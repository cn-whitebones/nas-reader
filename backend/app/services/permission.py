"""权限校验服务:判断用户对文件源/图书的读取权限,并生成查询过滤条件。

规则:
- 管理员拥有全部权限
- 普通用户按 permissions 表授权:授予到 source 级;若某条带 sub_path,则仅该子路径(及其下)可读
- 无匹配授权则不可读
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book import Book
from app.models.user import Permission, User, UserRole


async def get_readable_source_map(db: AsyncSession, user: User) -> dict[uuid.UUID, list[str | None]]:
    """返回用户可读的 {source_id: [sub_path 或 None, ...]}。

    列表含 None 表示整个源可读;否则仅列出的子路径前缀可读。
    管理员返回空 dict,调用方据 is_admin 放行全部。
    """
    if user.role == UserRole.admin:
        return {}
    result = await db.execute(
        select(Permission).where(
            Permission.user_id == user.id, Permission.can_read.is_(True)
        )
    )
    mapping: dict[uuid.UUID, list[str | None]] = {}
    for perm in result.scalars().all():
        mapping.setdefault(perm.source_id, []).append(perm.sub_path)
    return mapping


def apply_book_filter(stmt: Select, user: User, source_map: dict[uuid.UUID, list[str | None]]) -> Select:
    """给 Book 查询语句追加权限过滤。管理员不加限制。"""
    if user.role == UserRole.admin:
        return stmt
    if not source_map:
        # 无任何授权:构造永假条件
        return stmt.where(Book.id == uuid.UUID(int=0))

    clauses = []
    for source_id, sub_paths in source_map.items():
        if None in sub_paths:
            clauses.append(Book.source_id == source_id)
        else:
            for sp in sub_paths:
                if sp:
                    # 子路径前缀匹配(该目录及其子目录)
                    clauses.append(
                        (Book.source_id == source_id)
                        & (or_(Book.dir_path == sp, Book.dir_path.like(f"{sp}/%")))
                    )
    return stmt.where(or_(*clauses)) if clauses else stmt.where(Book.id == uuid.UUID(int=0))


async def can_read_book(db: AsyncSession, user: User, book: Book) -> bool:
    """判断用户能否读取某本书。"""
    if user.role == UserRole.admin:
        return True
    source_map = await get_readable_source_map(db, user)
    sub_paths = source_map.get(book.source_id)
    if sub_paths is None:
        return False
    if None in sub_paths:
        return True
    return any(sp and (book.dir_path == sp or book.dir_path.startswith(f"{sp}/")) for sp in sub_paths)


async def get_readable_book(
    db: AsyncSession, user: User, book_id: uuid.UUID
) -> Book:
    """按 ID 获取图书并校验可读权限。失败抛出 HTTPException。"""
    book = await db.get(Book, book_id, options=[selectinload(Book.book_metadata)])
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图书不存在")
    if not await can_read_book(db, user, book):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该图书")
    return book
