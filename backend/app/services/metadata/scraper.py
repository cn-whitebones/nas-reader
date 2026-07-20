"""刮削编排:多源降级搜索、把选定候选写入图书元数据。"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import httpx

from app.core.config import settings
from app.models.book import BookMetadata, MetadataProviderName
from app.services.metadata.base import (
    MetadataCandidate,
    MetadataProvider,
    ScrapeTracer,
)
from app.services.metadata.douban import DoubanProvider
from app.services.metadata.google import GoogleBooksProvider
from app.services.metadata.openlibrary import OpenLibraryProvider
from app.services.sortkey import authors_sort_key, to_sort_key
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

_PROVIDER_LABEL = {
    MetadataProviderName.douban: "豆瓣读书",
    MetadataProviderName.google: "Google Books",
    MetadataProviderName.openlibrary: "Open Library",
}


async def search_candidates(
    keyword: str,
    provider: MetadataProviderName | None = None,
    limit: int = 5,
    tracer: ScrapeTracer | None = None,
    douban_cookie: str | None = None,
    order: list[MetadataProviderName] | None = None,
) -> list[MetadataCandidate]:
    """搜索候选。指定 provider 则只用该源;否则按降级链依次尝试,首个有结果即返回。

    过程写入 tracer(若提供),供前端可视化展示。
    douban_cookie 若提供,则用它构造豆瓣 Provider(覆盖环境变量默认值)。
    order 若提供,则作为自动模式的降级顺序(仅含已启用的源);否则用内置默认顺序。
    """
    tracer = tracer or ScrapeTracer()
    providers = dict(_PROVIDERS)
    if douban_cookie is not None:
        providers[MetadataProviderName.douban] = DoubanProvider(cookie=douban_cookie)

    if provider is not None:
        tracer.info("", f"指定来源:{_PROVIDER_LABEL.get(provider, provider.value)}")
        p = providers.get(provider)
        if not p:
            tracer.error("", f"未知来源:{provider}")
            return []
        result = await p.search(keyword, limit, tracer)
        if not result:
            tracer.warning("", "该来源未返回任何候选")
        return result

    fallback = order if order is not None else _FALLBACK_ORDER
    if not fallback:
        tracer.warning("", "没有已启用的刮削源,请在刮削设置中启用至少一个来源")
        return []
    chain = " → ".join(_PROVIDER_LABEL.get(n, n.value) for n in fallback)
    tracer.info("", f"自动模式:按「{chain}」顺序降级尝试")
    for name in fallback:
        candidates = await providers[name].search(keyword, limit, tracer)
        if candidates:
            tracer.success("", f"命中来源:{_PROVIDER_LABEL.get(name, name.value)},停止降级")
            return candidates
        tracer.info("", f"{_PROVIDER_LABEL.get(name, name.value)} 无结果,降级到下一来源")
    tracer.warning("", "所有来源均无结果")
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
    # 同步拼音排序键(书库按名称/作者排序用)
    md.title_sort = to_sort_key(md.title or "")
    md.author_sort = authors_sort_key(md.authors)

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
