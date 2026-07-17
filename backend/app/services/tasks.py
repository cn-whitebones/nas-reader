"""后台任务调度器(进程内 APScheduler)。

- 提供全局 scheduler 实例(应用启动时 start)
- enqueue_scan:创建 ScanTask 并异步执行一次扫描
- register_auto_scans:为开启 auto_scan 的文件源注册周期任务

关键设计:扫描是 CPU/IO 密集的**同步阻塞**操作(遍历目录、读文件、解析
整本书、算哈希)。若把 async 的 run_scan 直接交给 AsyncIOScheduler,它会
在 uvicorn 的**同一个事件循环**上执行,一次大扫描就会阻塞整个事件循环——
期间所有 HTTP 请求(含前端轮询)无响应、后续任务无法调度,表现为任务一直
卡在「等待中(pending)」。因此扫描 job 走独立线程池执行器(ThreadPoolExecutor),
在线程内用 asyncio.run 起独立事件循环跑 run_scan,与主循环彻底隔离。
"""
from __future__ import annotations

import asyncio
import uuid

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import AsyncSessionLocal
from app.models.source import ScanTask, Source
from app.services.scanner.scan import run_scan

# 所有 job 走线程池执行器,避免阻塞 uvicorn 事件循环;并发上限适度即可(扫描以磁盘 IO 为主)
scheduler = AsyncIOScheduler(executors={"default": ThreadPoolExecutor(4)})


def _run_scan_in_thread(source_id: uuid.UUID, task_id: uuid.UUID, force: bool) -> None:
    """线程池执行体:在独立事件循环里跑 async 的 run_scan,不触碰主事件循环。"""
    asyncio.run(run_scan(source_id, task_id, force))


async def enqueue_scan(source_id: uuid.UUID, force: bool = False) -> uuid.UUID:
    """创建扫描任务并调度立即执行,返回 task_id。force 时强制重解析所有文件。"""
    async with AsyncSessionLocal() as db:
        task = ScanTask(source_id=source_id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    scheduler.add_job(
        _run_scan_in_thread,
        args=[source_id, task_id, force],
        id=f"scan-{task_id}",
        misfire_grace_time=None,
    )
    return task_id


def _auto_job_id(source_id: uuid.UUID) -> str:
    return f"autoscan-{source_id}"


def _auto_scan_job(source_id: uuid.UUID) -> None:
    """周期自动扫描:同样在线程里执行,避免阻塞主循环。"""
    asyncio.run(enqueue_scan(source_id))


def schedule_auto_scan(source: Source) -> None:
    """按 source 配置注册/更新周期扫描;auto_scan 关闭则移除。"""
    job_id = _auto_job_id(source.id)
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)
    if source.auto_scan and source.enabled:
        scheduler.add_job(
            _auto_scan_job,
            trigger="interval",
            minutes=max(source.scan_interval_minutes, 1),
            args=[source.id],
            id=job_id,
            misfire_grace_time=300,
        )


async def register_auto_scans() -> None:
    """应用启动时:为所有开启自动扫描的文件源注册周期任务。"""
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Source).where(Source.auto_scan.is_(True), Source.enabled.is_(True))
        )
        for source in result.scalars().all():
            schedule_auto_scan(source)
