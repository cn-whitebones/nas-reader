"""刮削路由:搜索候选、触发刮削、应用候选、手动编辑元数据、封面图片代理、流式刮削。"""
import asyncio
import json
import os
import uuid
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.book import Book, BookMetadata, MetadataProviderName
from app.models.user import User
from app.schemas.book import MetadataOut, MetadataUpdate
from app.schemas.scrape import (
    ApplyCandidateRequest,
    CandidateOut,
    ScrapeRequest,
    ScrapeResult,
    ScrapeStepOut,
)
from app.services.metadata.base import MetadataCandidate, ScrapeStep, ScrapeTracer
from app.services.metadata.scraper import apply_candidate, search_candidates
from app.services.settings_store import get_douban_cookie, get_provider_config
from app.services.sortkey import authors_sort_key, to_sort_key
from app.services.permission import can_read_book, get_readable_book

router = APIRouter(tags=["scrape"])


async def _enabled_order(db: AsyncSession) -> list[MetadataProviderName]:
    """从刮削源配置解析出「已启用」的源顺序,供自动降级使用。"""
    config = await get_provider_config(db)
    order: list[MetadataProviderName] = []
    for item in config:
        if item.get("enabled"):
            try:
                order.append(MetadataProviderName(item["provider"]))
            except ValueError:
                continue
    return order


def _to_result(keyword: str, candidates, tracer: ScrapeTracer) -> ScrapeResult:
    return ScrapeResult(
        keyword=keyword,
        candidates=[CandidateOut(**c.__dict__) for c in candidates],
        steps=[ScrapeStepOut(**s.__dict__) for s in tracer.steps],
    )


@router.get("/scrape/cover-proxy")
async def scrape_cover_proxy(
    url: str = Query(min_length=1, max_length=1000),
    _user: User = Depends(get_current_admin),
):
    """代理拉取候选封面图片。

    豆瓣等图床有 Referer 防盗链,浏览器直接 <img src> 请求会被拒(403),
    导致候选封面在预览时加载失败。此处后端带 Referer 拉图后回传,仅管理员可用。
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法图片地址")
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://book.douban.com/"}
    try:
        async with httpx.AsyncClient(
            timeout=settings.scrape_timeout_seconds, headers=headers, follow_redirects=True
        ) as client:
            resp = await client.get(url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="图片拉取失败")
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"图源返回 {resp.status_code}")
    media_type = resp.headers.get("Content-Type", "image/jpeg")
    return Response(content=resp.content, media_type=media_type)


@router.get("/scrape/search", response_model=ScrapeResult)
async def scrape_search(
    keyword: str = Query(min_length=1, max_length=200),
    provider: MetadataProviderName | None = None,
    limit: int = Query(5, ge=1, le=10),
    _user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """独立搜索候选(不绑定具体图书)。仅管理员可用。返回候选与刮削过程日志。"""
    tracer = ScrapeTracer()
    cookie = await get_douban_cookie(db)
    order = await _enabled_order(db)
    candidates = await search_candidates(
        keyword, provider, limit, tracer, douban_cookie=cookie, order=order
    )
    return _to_result(keyword, candidates, tracer)


@router.get("/scrape/stream")
async def scrape_stream(
    keyword: str = Query(min_length=1, max_length=200),
    provider: MetadataProviderName | None = None,
    limit: int = Query(5, ge=1, le=10),
    _user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """流式刮削(SSE):实时推送每一步过程,结束时推送候选结果。仅管理员可用。

    事件格式:
      event: step  data: {provider, level, message, elapsed_ms}
      event: done  data: {candidates: [...]}
      event: error data: {message}
    """
    cookie = await get_douban_cookie(db)
    order = await _enabled_order(db)
    queue: asyncio.Queue[ScrapeStep] = asyncio.Queue()
    tracer = ScrapeTracer()
    tracer.set_queue(queue)

    async def run() -> list:
        return await search_candidates(
            keyword, provider, limit, tracer, douban_cookie=cookie, order=order
        )

    async def event_gen() -> AsyncGenerator[str, None]:
        task = asyncio.create_task(run())
        try:
            # 边跑边刷:任务未完成或队列还有残留就持续吐 step 事件
            while not task.done() or not queue.empty():
                try:
                    step = await asyncio.wait_for(queue.get(), timeout=0.3)
                except asyncio.TimeoutError:
                    continue
                yield _sse("step", step.__dict__)
            candidates = await task
            payload = {"candidates": [CandidateOut(**c.__dict__).model_dump() for c in candidates]}
            yield _sse("done", payload)
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/scrape/books/{book_id}/scrape", response_model=ScrapeResult)
async def scrape_book(
    book_id: uuid.UUID,
    payload: ScrapeRequest,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """为图书搜索候选。关键词默认取已有标题或文件名(去扩展名)。仅管理员可用。"""
    book = await get_readable_book(db, user, book_id)
    keyword = payload.keyword
    if not keyword:
        md = await db.get(BookMetadata, book_id)
        keyword = (md.title if md and md.title else None) or os.path.splitext(book.file_name)[0]
    tracer = ScrapeTracer()
    cookie = await get_douban_cookie(db)
    order = await _enabled_order(db)
    candidates = await search_candidates(
        keyword, payload.provider, payload.limit, tracer, douban_cookie=cookie, order=order
    )
    return _to_result(keyword, candidates, tracer)


@router.post("/scrape/books/{book_id}/metadata/apply", response_model=MetadataOut)
async def apply_metadata(
    book_id: uuid.UUID,
    payload: ApplyCandidateRequest,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """把选定候选写入图书元数据(含下载封面)。仅管理员可用。"""
    await get_readable_book(db, user, book_id)
    candidate = MetadataCandidate(**payload.candidate.model_dump())
    md = await apply_candidate(db, book_id, candidate)
    return MetadataOut.model_validate(md)


@router.patch("/scrape/books/{book_id}/metadata", response_model=MetadataOut)
async def update_metadata(
    book_id: uuid.UUID,
    payload: MetadataUpdate,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """手动编辑/兜底录入元数据。仅管理员可用。"""
    await get_readable_book(db, user, book_id)
    md = await db.get(BookMetadata, book_id)
    if md is None:
        md = BookMetadata(book_id=book_id)
        db.add(md)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(md, key, value)
    md.source_provider = MetadataProviderName.manual
    # 同步拼音排序键(标题/作者可能被修改)
    md.title_sort = to_sort_key(md.title or "")
    md.author_sort = authors_sort_key(md.authors)
    await db.commit()
    await db.refresh(md)
    return MetadataOut.model_validate(md)
