"""文件源管理与扫描路由(仅管理员)。"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.source import ScanTask, Source
from app.schemas.source import ScanTaskOut, SourceCreate, SourceOut, SourceUpdate
from app.services.scanner.fsutil import is_within
from app.services.tasks import enqueue_scan, schedule_auto_scan

router = APIRouter(tags=["sources"], dependencies=[Depends(get_current_admin)])


def _validate_root(path: str) -> None:
    """文件源根目录必须位于 DATA_ROOT 之下且存在,防止访问容器内任意路径。"""
    if not is_within(settings.data_root, path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径必须位于 {settings.data_root} 之下(容器内挂载路径)",
        )
    if not os.path.isdir(path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="目录不存在或不可访问")


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(Source.created_at.desc()))
    return list(result.scalars().all())


@router.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreate, db: AsyncSession = Depends(get_db)):
    _validate_root(payload.root_path)
    exists = await db.scalar(select(Source.id).where(Source.root_path == payload.root_path))
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该路径已是文件源")
    source = Source(**payload.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    schedule_auto_scan(source)
    return source


@router.patch("/sources/{source_id}", response_model=SourceOut)
async def update_source(source_id: uuid.UUID, payload: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件源不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    await db.commit()
    await db.refresh(source)
    schedule_auto_scan(source)
    return source


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件源不存在")
    await db.delete(source)
    await db.commit()


@router.post("/sources/{source_id}/scan", response_model=ScanTaskOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_scan(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件源不存在")
    task_id = await enqueue_scan(source_id)
    task = await db.get(ScanTask, task_id)
    return task


@router.get("/scan-tasks/{task_id}", response_model=ScanTaskOut)
async def get_scan_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(ScanTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.get("/sources/{source_id}/scan-tasks", response_model=list[ScanTaskOut])
async def list_scan_tasks(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScanTask).where(ScanTask.source_id == source_id).order_by(ScanTask.created_at.desc()).limit(20)
    )
    return list(result.scalars().all())
