"""Open Library 元数据 Provider(官方 API,免费无需 key)。"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.book import MetadataProviderName
from app.services.metadata.base import MetadataCandidate, MetadataProvider

_SEARCH = "https://openlibrary.org/search.json"
_COVER = "https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"


class OpenLibraryProvider(MetadataProvider):
    name = MetadataProviderName.openlibrary

    async def search(self, keyword: str, limit: int = 5) -> list[MetadataCandidate]:
        try:
            async with httpx.AsyncClient(timeout=settings.scrape_timeout_seconds) as client:
                resp = await client.get(
                    _SEARCH,
                    params={"q": keyword, "limit": limit, "fields": "title,author_name,first_publish_year,isbn,language,cover_i,subject"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        candidates: list[MetadataCandidate] = []
        for doc in data.get("docs", [])[:limit]:
            cover_id = doc.get("cover_i")
            isbns = doc.get("isbn") or []
            candidates.append(
                MetadataCandidate(
                    provider=self.name,
                    title=doc.get("title", ""),
                    authors=doc.get("author_name", []),
                    isbn=isbns[0] if isbns else None,
                    pub_date=str(doc.get("first_publish_year")) if doc.get("first_publish_year") else None,
                    language=(doc.get("language") or [None])[0],
                    tags=(doc.get("subject") or [])[:8],
                    cover_url=_COVER.format(cover_id=cover_id) if cover_id else None,
                )
            )
        return candidates
