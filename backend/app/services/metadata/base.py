"""元数据 Provider 抽象层。

每个来源实现 MetadataProvider,提供 search(关键词 → 候选列表)。
多源以降级链方式组合:豆瓣(抓取,不稳定)→ Google Books → Open Library。
新增来源只需实现子类并注册。
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.book import MetadataProviderName


@dataclass
class ScrapeStep:
    """刮削过程中的一步记录,用于前端可视化展示。"""

    provider: str  # 来源标识,如 douban / google / openlibrary,或 "" 表示编排层
    level: str  # info | success | warning | error
    message: str  # 人类可读的过程描述
    elapsed_ms: int | None = None  # 该步耗时(毫秒),可选


class ScrapeTracer:
    """收集刮削过程步骤。Provider 与编排层往里写,API 层读出返回给前端。"""

    def __init__(self) -> None:
        self.steps: list[ScrapeStep] = []

    def add(
        self, provider: str, level: str, message: str, elapsed_ms: int | None = None
    ) -> None:
        self.steps.append(ScrapeStep(provider=provider, level=level, message=message, elapsed_ms=elapsed_ms))

    def info(self, provider: str, message: str, elapsed_ms: int | None = None) -> None:
        self.add(provider, "info", message, elapsed_ms)

    def success(self, provider: str, message: str, elapsed_ms: int | None = None) -> None:
        self.add(provider, "success", message, elapsed_ms)

    def warning(self, provider: str, message: str, elapsed_ms: int | None = None) -> None:
        self.add(provider, "warning", message, elapsed_ms)

    def error(self, provider: str, message: str, elapsed_ms: int | None = None) -> None:
        self.add(provider, "error", message, elapsed_ms)


def now_ms() -> float:
    """单调时钟毫秒,用于计算各步骤耗时。"""
    return time.monotonic() * 1000


class _NullTracer(ScrapeTracer):
    """默认空追踪器:Provider 在未传 tracer 时使用,不产生开销。"""

    def add(self, *args, **kwargs) -> None:  # noqa: D401
        pass


NULL_TRACER = _NullTracer()


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
    async def search(
        self, keyword: str, limit: int = 5, tracer: ScrapeTracer = NULL_TRACER
    ) -> list[MetadataCandidate]:
        """按关键词搜索,返回候选列表。失败应返回空列表而非抛出。

        实现应把关键过程(请求 URL、HTTP 状态、抓取条数、异常)写入 tracer,
        供前端可视化展示。
        """
        raise NotImplementedError
