"""刮削编排:多源降级搜索、把选定候选写入图书元数据。"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import httpx

from app.core.config import settings
from app.models.book import BookMetadata, MetadataProviderName
from app.services.metadata.base import MetadataCandidate, MetadataProvider
from app.services.metadata.douban import DoubanProvider
from app.services.metadata.google import GoogleBooksProvider
from app.services.metadata.openlibrary import OpenLibraryProvider
from app.services.scanner.covers import save_cover

# 降级顺序:豆瓣(中文书友好但不稳定)→ Google → Open Library
_PROVIDERS: dict[MetadataProviderName, MetadataProvider] = {
    MetadataProviderName.douban: DoubanProvider(),
    MetadataProviderName.google: GoogleBooksProvider(),
    MetadataProviderName.openlibrary: OpenLibraryProvider(),
}
_FALLBACK_ORDER = [
    MetadataProviderName.douban,
    MetadataProviderName.google,
    MetadataProviderName.openlibrary,
]


async def search_candidates(
    keyword: str, provider: MetadataProviderName | None = None, limit: int = 5
) -> list[MetadataCandidate]:
    """搜索候选。指定 provider 则只用该源;否则按降级链依次尝试,首个有结果即返回。"""
    if provider is not None:
        p = _PROVIDERS.get(provider)
        return await p.search(keyword, limit) if p else []

    for name in _FALLBACK_ORDER:
        candidates = await _PROVIDERS[name].search(keyword, limit)
        if candidates:
            return candidates
    return []


def _parse_pub_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # 尝试从中提取 4 位年份
    import re

    m = re.search(r"(\d{4})", raw)
    if m:
        try:
            return date(int(m.group(1)), 1, 1)
        except ValueError:
            return None
    return None


async def apply_candidate(db, book_id: uuid.UUID, candidate: MetadataCandidate) -> BookMetadata:
    """把候选写入 book_metadata(upsert),并尝试下载封面。"""
    md = await db.get(BookMetadata, book_id)
    if md is None:
        md = BookMetadata(book_id=book_id)
        db.add(md)

    md.title = candidate.title or md.title
    md.subtitle = candidate.subtitle
    md.authors = candidate.authors or []
    md.publisher = candidate.publisher
    md.isbn = candidate.isbn
    md.pub_date = _parse_pub_date(candidate.pub_date)
    md.description = candidate.description
    md.language = candidate.language
    md.tags = candidate.tags or []
    md.rating = candidate.rating
    md.douban_id = candidate.external_id if candidate.provider == MetadataProviderName.douban else md.douban_id
    md.source_provider = candidate.provider
    md.scraped_at = datetime.now(timezone.utc)

    # 下载封面(失败忽略)
    if candidate.cover_url:
        cover_bytes = await _download(candidate.cover_url)
        if cover_bytes:
            from app.models.book import Book

            filename = save_cover(str(book_id), cover_bytes)
            if filename:
                book = await db.get(Book, book_id)
                if book:
                    book.cover_path = filename

    await db.commit()
    await db.refresh(md)
    return md


async def _download(url: str) -> bytes | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://book.douban.com/"}
        async with httpx.AsyncClient(timeout=settings.scrape_timeout_seconds, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None
