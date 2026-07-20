"""Pydantic schemas:刮削候选与请求。"""
from pydantic import BaseModel

from app.models.book import MetadataProviderName


class CandidateOut(BaseModel):
    provider: MetadataProviderName
    title: str
    subtitle: str | None = None
    authors: list[str] = []
    publisher: str | None = None
    isbn: str | None = None
    pub_date: str | None = None
    description: str | None = None
    language: str | None = None
    tags: list[str] = []
    rating: float | None = None
    cover_url: str | None = None
    external_id: str | None = None


class ScrapeStepOut(BaseModel):
    """刮削过程中的一步,供前端可视化。"""

    provider: str
    level: str  # info | success | warning | error
    message: str
    elapsed_ms: int | None = None


class ScrapeResult(BaseModel):
    """刮削结果:候选列表 + 过程日志。"""

    keyword: str
    candidates: list[CandidateOut] = []
    steps: list[ScrapeStepOut] = []


class ScrapeRequest(BaseModel):
    """触发刮削:可指定关键词(默认用书名/文件名)与来源。"""

    keyword: str | None = None
    provider: MetadataProviderName | None = None
    limit: int = 5


class ApplyCandidateRequest(BaseModel):
    """把某个候选应用到图书。"""

    candidate: CandidateOut
