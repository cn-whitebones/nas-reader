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
from app.services.metadata.base import (
    NULL_TRACER,
    MetadataCandidate,
    MetadataProvider,
    ScrapeTracer,
    now_ms,
)

_SEARCH_URL = "https://www.douban.com/search"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
# 豆瓣搜索结果里的书籍链接是 URL 编码的跳转链接
# (如 link2/?url=https%3A%2F%2Fbook.douban.com%2Fsubject%2F3066477%2F),
# 同时兼容明文 book/subject/123 与编码 %2Fsubject%2F123 两种形式。
_SUBJECT_RE = re.compile(r"subject(?:/|%2F)(\d+)")


class DoubanProvider(MetadataProvider):
    name = MetadataProviderName.douban

    def __init__(self, cookie: str | None = None) -> None:
        # cookie 为 None 时回退到环境变量;调用方(编排层)可注入 DB 中配置的 Cookie
        self._cookie = cookie if cookie is not None else settings.douban_cookie

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": _UA, "Referer": "https://www.douban.com/"}
        if self._cookie:
            headers["Cookie"] = self._cookie
        return headers

    async def search(
        self, keyword: str, limit: int = 5, tracer: ScrapeTracer = NULL_TRACER
    ) -> list[MetadataCandidate]:
        started = now_ms()
        has_cookie = bool(self._cookie)
        tracer.info(
            "douban",
            f"抓取豆瓣搜索页,关键词「{keyword}」({'已配置 Cookie' if has_cookie else '未配置 Cookie,易被限流'})",
        )
        try:
            async with httpx.AsyncClient(
                timeout=settings.scrape_timeout_seconds, headers=self._headers(), follow_redirects=True
            ) as client:
                resp = await client.get(_SEARCH_URL, params={"cat": "1001", "q": keyword})
                if resp.status_code != 200:
                    tracer.error("douban", f"搜索页返回 HTTP {resp.status_code}", int(now_ms() - started))
                    return []
                # 反爬检测:豆瓣限流时会返回登录/验证页而非正常搜索结果
                if self._looks_blocked(resp.text):
                    tracer.warning(
                        "douban",
                        "疑似被反爬拦截(返回登录或验证页)。可在设置中配置 DOUBAN_COOKIE 提高成功率",
                        int(now_ms() - started),
                    )
                    return []
                subject_ids = self._extract_subject_ids(resp.text, limit)
                if not subject_ids:
                    tracer.warning("douban", "搜索页未解析到任何书籍条目(可能无匹配或页面结构变化)", int(now_ms() - started))
                    return []
                tracer.info("douban", f"搜索页解析到 {len(subject_ids)} 个书籍条目,逐个抓取详情", int(now_ms() - started))
                candidates: list[MetadataCandidate] = []
                for sid in subject_ids:
                    cand = await self._fetch_subject(client, sid, tracer)
                    if cand:
                        candidates.append(cand)
                if candidates:
                    tracer.success("douban", f"成功抓取 {len(candidates)} 个候选", int(now_ms() - started))
                else:
                    tracer.warning("douban", "所有详情页抓取均失败", int(now_ms() - started))
                return candidates
        except httpx.TimeoutException:
            tracer.error("douban", f"请求超时(>{settings.scrape_timeout_seconds}s)", int(now_ms() - started))
            return []
        except Exception as e:
            tracer.error("douban", f"请求失败:{type(e).__name__}: {e}", int(now_ms() - started))
            return []

    @staticmethod
    def _looks_blocked(html: str) -> bool:
        """粗略判断豆瓣是否返回了反爬拦截页而非正常内容。"""
        markers = ("检测到有异常请求", "sec.douban.com", "有异常请求从你的 IP", "window.location.href='https://sec.douban.com")
        return any(m in html for m in markers)

    def _extract_subject_ids(self, html: str, limit: int) -> list[str]:
        ids: list[str] = []
        for m in _SUBJECT_RE.finditer(html):
            sid = m.group(1)
            if sid not in ids:
                ids.append(sid)
            if len(ids) >= limit:
                break
        return ids

    async def _fetch_subject(
        self, client: httpx.AsyncClient, subject_id: str, tracer: ScrapeTracer = NULL_TRACER
    ) -> MetadataCandidate | None:
        try:
            resp = await client.get(f"https://book.douban.com/subject/{subject_id}/")
            if resp.status_code != 200:
                tracer.warning("douban", f"详情页 {subject_id} 返回 HTTP {resp.status_code}")
                return None
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            tracer.warning("douban", f"详情页 {subject_id} 抓取失败:{type(e).__name__}")
            return None

        title = self._text(soup.select_one('h1 span[property="v:itemreviewed"]')) or self._text(
            soup.select_one("h1 span")
        )
        if not title:
            tracer.warning("douban", f"详情页 {subject_id} 未解析到书名")
            return None

        info = soup.select_one("#info")

        # 作者:优先取 #info 里「作者/译者」label 对应的 <a> 链接文本(最准);
        # 无链接时回退到文本解析。
        authors = self._extract_authors(info)
        # 其余字段用归一化后的整块文本按标签边界提取
        # (豆瓣 #info 里 label、冒号、值常被换行拆开,逐行 startswith 会失败)
        info_text = self._normalize_info(info)
        publisher = self._field(info_text, "出版社") or None
        pub_date = self._field(info_text, "出版年") or None
        isbn = self._field(info_text, "ISBN") or None

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

    # 豆瓣 #info 中的已知字段标签,用作正则切分的边界
    _INFO_LABELS = (
        "作者", "出版社", "出品方", "副标题", "原作名", "译者", "出版年",
        "页数", "定价", "装帧", "丛书", "ISBN", "统一书号", "出版时间",
    )

    @classmethod
    def _extract_authors(cls, info) -> list[str]:
        """从 #info 提取作者/译者:取「作者」label 后紧邻的 <a> 链接文本。"""
        if info is None:
            return []
        authors: list[str] = []
        for span in info.find_all("span", class_="pl"):
            label = span.get_text(strip=True)
            if label.startswith("作者") or label.startswith("译者"):
                # 收集该 label 之后、下一个 label 之前的 <a>
                node = span.next_sibling
                while node is not None:
                    name = getattr(node, "name", None)
                    if name == "span" and "pl" in (node.get("class") or []):
                        break  # 到达下一个字段标签
                    if name == "a":
                        text = node.get_text(strip=True)
                        if text and text not in authors:
                            authors.append(text)
                    node = node.next_sibling
        return authors

    @classmethod
    def _normalize_info(cls, info) -> str:
        """把 #info 拍平成单行文本并归一化冒号周围空白,便于按标签边界正则提取。"""
        if info is None:
            return ""
        text = info.get_text(" ", strip=True)
        return re.sub(r"\s*[:：]\s*", ":", text)

    @classmethod
    def _field(cls, info_text: str, label: str) -> str:
        """从归一化文本中提取 '标签:值',值截止到下一个已知标签或末尾。"""
        boundary = "|".join(cls._INFO_LABELS)
        m = re.search(rf"{label}:(.+?)(?: (?:{boundary}):|$)", info_text)
        return m.group(1).strip() if m else ""
