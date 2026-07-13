"""后台任务调度器(进程内 APScheduler)。

- 提供全局 scheduler 实例(应用启动时 start)
- enqueue_scan:创建 ScanTask 并异步执行一次扫描
- register_auto_scans:为开启 auto_scan 的文件源注册周期任务
"""
from __future__ import annotations

import uuid

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import AsyncSessionLocal
from app.models.source import ScanTask, Source
from app.services.scanner.scan import run_scan

scheduler = AsyncIOScheduler()


async def enqueue_scan(source_id: uuid.UUID, force: bool = False) -> uuid.UUID:
    """创建扫描任务并调度立即执行,返回 task_id。force 时强制重解析所有文件。"""
    async with AsyncSessionLocal() as db:
        task = ScanTask(source_id=source_id)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        task_id = task.id

    scheduler.add_job(
        run_scan, args=[source_id, task_id, force], id=f"scan-{task_id}", misfire_grace_time=None
    )
    return task_id


def _auto_job_id(source_id: uuid.UUID) -> str:
    return f"autoscan-{source_id}"


async def _auto_scan_job(source_id: uuid.UUID) -> None:
    await enqueue_scan(source_id)


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
