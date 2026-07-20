"""Google Books 元数据 Provider(官方 API,免费无需 key)。"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.book import MetadataProviderName
from app.services.metadata.base import (
    NULL_TRACER,
    MetadataCandidate,
    MetadataProvider,
    ScrapeTracer,
    now_ms,
)

_API = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksProvider(MetadataProvider):
    name = MetadataProviderName.google

    async def search(
        self, keyword: str, limit: int = 5, tracer: ScrapeTracer = NULL_TRACER
    ) -> list[MetadataCandidate]:
        started = now_ms()
        tracer.info("google", f"请求 Google Books API,关键词「{keyword}」")
        try:
            async with httpx.AsyncClient(timeout=settings.scrape_timeout_seconds) as client:
                resp = await client.get(_API, params={"q": keyword, "maxResults": limit})
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            tracer.error("google", f"请求超时(>{settings.scrape_timeout_seconds}s),可能网络无法访问 Google", int(now_ms() - started))
            return []
        except httpx.HTTPStatusError as e:
            tracer.error("google", f"HTTP {e.response.status_code} 错误", int(now_ms() - started))
            return []
        except Exception as e:
            tracer.error("google", f"请求失败:{type(e).__name__}: {e}", int(now_ms() - started))
            return []

        items = data.get("items", [])
        tracer.info("google", f"API 返回 {len(items)} 条原始结果", int(now_ms() - started))

        candidates: list[MetadataCandidate] = []
        for item in items[:limit]:
            info = item.get("volumeInfo", {})
            isbn = None
            for ident in info.get("industryIdentifiers", []):
                if ident.get("type") in ("ISBN_13", "ISBN_10"):
                    isbn = ident.get("identifier")
                    break
            candidates.append(
                MetadataCandidate(
                    provider=self.name,
                    title=info.get("title", ""),
                    subtitle=info.get("subtitle"),
                    authors=info.get("authors", []),
                    publisher=info.get("publisher"),
                    isbn=isbn,
                    pub_date=info.get("publishedDate"),
                    description=info.get("description"),
                    language=info.get("language"),
                    tags=info.get("categories", []),
                    rating=info.get("averageRating"),
                    cover_url=(info.get("imageLinks") or {}).get("thumbnail"),
                    external_id=item.get("id"),
                )
            )
        tracer.success("google", f"解析出 {len(candidates)} 个候选", int(now_ms() - started))
        return candidates
