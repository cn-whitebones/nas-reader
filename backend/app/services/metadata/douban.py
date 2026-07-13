"""豆瓣读书元数据 Provider(网页抓取,尽力而为)。

豆瓣官方 API 已于 2020 年关闭,此处通过搜索页 + 详情页抓取。
豆瓣反爬严格:未配置 cookie 时极易被限流/返回验证页,失败即返回空,
由上层降级到 Google Books / Open Library。可选配置 DOUBAN_COOKIE 提高成功率。
"""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.models.book import MetadataProviderName
from app.services.metadata.base import MetadataCandidate, MetadataProvider

_SEARCH_URL = "https://www.douban.com/search"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_SUBJECT_RE = re.compile(r"book/subject/(\d+)")


class DoubanProvider(MetadataProvider):
    name = MetadataProviderName.douban

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": _UA, "Referer": "https://www.douban.com/"}
        if settings.douban_cookie:
            headers["Cookie"] = settings.douban_cookie
        return headers

    async def search(self, keyword: str, limit: int = 5) -> list[MetadataCandidate]:
        try:
            async with httpx.AsyncClient(
                timeout=settings.scrape_timeout_seconds, headers=self._headers(), follow_redirects=True
            ) as client:
                resp = await client.get(_SEARCH_URL, params={"cat": "1001", "q": keyword})
                if resp.status_code != 200:
                    return []
                subject_ids = self._extract_subject_ids(resp.text, limit)
                candidates: list[MetadataCandidate] = []
                for sid in subject_ids:
                    cand = await self._fetch_subject(client, sid)
                    if cand:
                        candidates.append(cand)
                return candidates
        except Exception:
            return []

    def _extract_subject_ids(self, html: str, limit: int) -> list[str]:
        ids: list[str] = []
        for m in _SUBJECT_RE.finditer(html):
            sid = m.group(1)
            if sid not in ids:
                ids.append(sid)
            if len(ids) >= limit:
                break
        return ids

    async def _fetch_subject(self, client: httpx.AsyncClient, subject_id: str) -> MetadataCandidate | None:
        try:
            resp = await client.get(f"https://book.douban.com/subject/{subject_id}/")
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception:
            return None

        title = self._text(soup.select_one('h1 span[property="v:itemreviewed"]')) or self._text(
            soup.select_one("h1 span")
        )
        if not title:
            return None

        info = soup.select_one("#info")
        info_text = info.get_text("\n", strip=True) if info else ""

        authors = self._extract_field(info_text, "作者").split("/") if "作者" in info_text else []
        authors = [a.strip() for a in authors if a.strip()]
        publisher = self._extract_field(info_text, "出版社") or None
        pub_date = self._extract_field(info_text, "出版年") or None
        isbn = self._extract_field(info_text, "ISBN") or None

        desc_el = soup.select_one("#link-report .intro, .related_info .intro")
        description = desc_el.get_text("\n", strip=True) if desc_el else None

        rating_el = soup.select_one("strong.rating_num")
        rating = None
        if rating_el and rating_el.text.strip():
            try:
                rating = float(rating_el.text.strip())
            except ValueError:
                rating = None

        tags = [t.get_text(strip=True) for t in soup.select("#db-tags-section .tag")][:8]
        cover_el = soup.select_one("#mainpic img")
        cover_url = cover_el.get("src") if cover_el else None

        return MetadataCandidate(
            provider=self.name,
            title=title,
            authors=authors,
            publisher=publisher,
            isbn=isbn,
            pub_date=pub_date,
            description=description,
            rating=rating,
            tags=tags,
            cover_url=cover_url,
            external_id=subject_id,
        )

    @staticmethod
    def _text(el) -> str | None:
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _extract_field(info_text: str, label: str) -> str:
        """从 #info 文本中提取 '标签: 值' 形式的值。"""
        for line in info_text.split("\n"):
            if line.startswith(label):
                return line.split(":", 1)[-1].split("：", 1)[-1].strip()
        return ""
