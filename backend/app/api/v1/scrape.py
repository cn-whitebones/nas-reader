"""刮削路由:搜索候选、触发刮削、应用候选、手动编辑元数据。"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, BookMetadata, MetadataProviderName
from app.models.user import User
from app.schemas.book import MetadataOut, MetadataUpdate
from app.schemas.scrape import ApplyCandidateRequest, CandidateOut, ScrapeRequest
from app.services.metadata.base import MetadataCandidate
from app.services.metadata.scraper import apply_candidate, search_candidates
from app.services.permission import can_read_book

router = APIRouter(tags=["scrape"])


@router.get("/scrape/search", response_model=list[CandidateOut])
async def scrape_search(
    keyword: str = Query(min_length=1, max_length=200),
    provider: MetadataProviderName | None = None,
    limit: int = Query(5, ge=1, le=10),
    _user: User = Depends(get_current_user),
):
    """独立搜索候选(不绑定具体图书)。"""
    candidates = await search_candidates(keyword, provider, limit)
    return [CandidateOut(**c.__dict__) for c in candidates]


@router.post("/books/{book_id}/scrape", response_model=list[CandidateOut])
async def scrape_book(
    book_id: uuid.UUID,
    payload: ScrapeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """为图书搜索候选。关键词默认取已有标题或文件名(去扩展名)。"""
    book = await _get_readable_book(db, user, book_id)
    keyword = payload.keyword
    if not keyword:
        md = await db.get(BookMetadata, book_id)
        keyword = (md.title if md and md.title else None) or os.path.splitext(book.file_name)[0]
    candidates = await search_candidates(keyword, payload.provider, payload.limit)
    return [CandidateOut(**c.__dict__) for c in candidates]


@router.post("/books/{book_id}/metadata/apply", response_model=MetadataOut)
async def apply_metadata(
    book_id: uuid.UUID,
    payload: ApplyCandidateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """把选定候选写入图书元数据(含下载封面)。"""
    await _get_readable_book(db, user, book_id)
    candidate = MetadataCandidate(**payload.candidate.model_dump())
    md = await apply_candidate(db, book_id, candidate)
    return MetadataOut.model_validate(md)


@router.put("/books/{book_id}/metadata", response_model=MetadataOut)
async def update_metadata(
    book_id: uuid.UUID,
    payload: MetadataUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """手动编辑/兜底录入元数据。"""
    await _get_readable_book(db, user, book_id)
    md = await db.get(BookMetadata, book_id)
    if md is None:
        md = BookMetadata(book_id=book_id)
        db.add(md)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(md, key, value)
    md.source_provider = MetadataProviderName.manual
    await db.commit()
    await db.refresh(md)
    return MetadataOut.model_validate(md)


async def _get_readable_book(db: AsyncSession, user: User, book_id: uuid.UUID) -> Book:
    book = await db.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图书不存在")
    if not await can_read_book(db, user, book):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该图书")
    return book
