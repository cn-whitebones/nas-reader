"""元数据 Provider 抽象层。

每个来源实现 MetadataProvider,提供 search(关键词 → 候选列表)。
多源以降级链方式组合:豆瓣(抓取,不稳定)→ Google Books → Open Library。
新增来源只需实现子类并注册。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.book import MetadataProviderName


@dataclass
class MetadataCandidate:
    """一个刮削候选结果。"""

    provider: MetadataProviderName
    title: str
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    isbn: str | None = None
    pub_date: str | None = None  # ISO 字符串或年份,入库时解析
    description: str | None = None
    language: str | None = None
    tags: list[str] = field(default_factory=list)
    rating: float | None = None
    cover_url: str | None = None
    external_id: str | None = None  # 豆瓣 id 等


class MetadataProvider(ABC):
    name: MetadataProviderName

    @abstractmethod
    async def search(self, keyword: str, limit: int = 5) -> list[MetadataCandidate]:
        """按关键词搜索,返回候选列表。失败应返回空列表而非抛出。"""
        raise NotImplementedError
