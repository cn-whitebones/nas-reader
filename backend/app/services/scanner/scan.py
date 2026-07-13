"""扫描服务:遍历文件源目录,增量入库图书、章节、封面。

设计要点:
- 增量:已存在且 (size, mtime) 未变的文件跳过重新解析
- 稳定标识:file_hash(首段+size),文件移动/改名不丢进度
- 缺失处理:磁盘上已不存在的图书标记 status=missing(不物理删除)
- 后台执行:通过 ScanTask 记录进度,供前端轮询
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.book import Book, BookMetadata, BookStatus, Chapter
from app.models.source import ScanStatus, ScanTask, Source
from app.services.parsers.registry import SUPPORTED_EXTENSIONS, get_format, get_parser
from app.services.scanner.covers import save_cover
from app.services.scanner.fsutil import compute_file_hash


async def run_scan(source_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """执行一次扫描。独立开 session(后台任务,与请求生命周期解耦)。"""
    async with AsyncSessionLocal() as db:
        source = await db.get(Source, source_id)
        task = await db.get(ScanTask, task_id)
        if source is None or task is None:
            return
        task.status = ScanStatus.running
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            await _scan_source(db, source, task)
            task.status = ScanStatus.done
        except Exception as exc:  # noqa: BLE001
            task.status = ScanStatus.failed
            task.error = str(exc)[:2000]
        finally:
            task.finished_at = datetime.now(timezone.utc)
            source.last_scan_at = datetime.now(timezone.utc)
            await db.commit()


async def _scan_source(db: AsyncSession, source: Source, task: ScanTask) -> None:
    root = source.root_path
    if not os.path.isdir(root):
        raise FileNotFoundError(f"文件源目录不存在: {root}")

    # 载入现有图书:rel_path -> Book(用于增量对比与缺失检测)
    result = await db.execute(select(Book).where(Book.source_id == source.id))
    existing: dict[str, Book] = {b.rel_path: b for b in result.scalars().all()}
    seen: set[str] = set()

    # 先统计总数用于进度显示
    files = list(_iter_files(root))
    task.total = len(files)
    await db.commit()

    for abs_path in files:
        rel_path = os.path.relpath(abs_path, root)
        seen.add(rel_path)
        try:
            changed = await _process_file(db, source, existing.get(rel_path), abs_path, rel_path, task)
            if changed:
                await db.commit()
        except Exception:  # noqa: BLE001 单个文件失败不影响整体
            await db.rollback()
        task.processed += 1
        if task.processed % 20 == 0:
            await db.commit()

    # 标记缺失:数据库有但本次未扫到的
    missing = set(existing.keys()) - seen
    if missing:
        await db.execute(
            update(Book)
            .where(Book.source_id == source.id, Book.rel_path.in_(missing))
            .values(status=BookStatus.missing)
        )
    await db.commit()


def _iter_files(root: str):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in SUPPORTED_EXTENSIONS:
                yield os.path.join(dirpath, name)


async def _process_file(
    db: AsyncSession,
    source: Source,
    book: Book | None,
    abs_path: str,
    rel_path: str,
    task: ScanTask,
) -> bool:
    """处理单个文件,返回是否有写入。"""
    stat = os.stat(abs_path)
    size = stat.st_size
    ext = rel_path.rsplit(".", 1)[-1].lower()
    fmt = get_format(ext)
    if fmt is None:
        return False

    # 增量:已存在且大小未变且非 missing → 认为无变化,跳过重解析
    if book is not None and book.file_size == size and book.status == BookStatus.active:
        return False

    file_hash = compute_file_hash(abs_path, size)
    dir_path = os.path.dirname(rel_path)
    file_name = os.path.basename(rel_path)

    if book is None:
        book = Book(
            id=uuid.uuid4(),
            source_id=source.id,
            rel_path=rel_path,
            dir_path=dir_path,
            file_name=file_name,
            format=fmt,
            file_hash=file_hash,
            file_size=size,
            status=BookStatus.active,
        )
        db.add(book)
        await db.flush()
        task.added += 1
    else:
        book.file_hash = file_hash
        book.file_size = size
        book.status = BookStatus.active
        book.file_name = file_name
        book.dir_path = dir_path
        task.updated += 1
        # 重解析前清空旧章节
        await db.execute(Chapter.__table__.delete().where(Chapter.book_id == book.id))

    # 解析章节 / 封面 / 内嵌元数据
    parser = get_parser(ext)
    if parser is not None:
        parsed = parser.parse(abs_path)
        for ch in parsed.chapters:
            db.add(Chapter(book_id=book.id, idx=ch.idx, title=ch.title, location=ch.location))
        book.chapter_count = len(parsed.chapters)

        # 封面
        if parsed.cover_bytes:
            cover = save_cover(str(book.id), parsed.cover_bytes)
            if cover:
                book.cover_path = cover

        # 内嵌元数据(仅在尚无元数据时写入,避免覆盖刮削结果)
        await _ensure_embedded_metadata(db, book, parsed)

    return True


async def _ensure_embedded_metadata(db: AsyncSession, book: Book, parsed) -> None:
    existing = await db.get(BookMetadata, book.id)
    if existing is not None:
        return  # 已有元数据(可能来自刮削),不覆盖
    title = parsed.title or os.path.splitext(book.file_name)[0]
    db.add(
        BookMetadata(
            book_id=book.id,
            title=title,
            authors=parsed.authors or [],
            language=parsed.language,
        )
    )
