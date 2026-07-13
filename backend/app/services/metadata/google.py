"""Google Books 元数据 Provider(官方 API,免费无需 key)。"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.models.book import MetadataProviderName
from app.services.metadata.base import MetadataCandidate, MetadataProvider

_API = "https://www.googleapis.com/books/v1/volumes"


class GoogleBooksProvider(MetadataProvider):
    name = MetadataProviderName.google

    async def search(self, keyword: str, limit: int = 5) -> list[MetadataCandidate]:
        try:
            async with httpx.AsyncClient(timeout=settings.scrape_timeout_seconds) as client:
                resp = await client.get(_API, params={"q": keyword, "maxResults": limit})
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        candidates: list[MetadataCandidate] = []
        for item in data.get("items", [])[:limit]:
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
        return candidates
