"""图书库路由:列表、目录树、详情、章节、阅读内容、文件流、封面、进度。"""
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.book import Book, BookFormat, BookMetadata, BookStatus, Chapter
from app.models.reading import ReadingProgress, ShelfBook
from app.models.source import Source
from app.models.user import User
from app.schemas.auth import Page
from app.schemas.book import (
    BookBrief,
    BookDetail,
    BookComicSettingsUpdate,
    ChapterContent,
    ChapterOut,
    MetadataOut,
    ProgressOut,
    ProgressUpdate,
    TreeNode,
)
from app.services.parsers.registry import get_parser
from app.services.permission import apply_book_filter, can_read_book, get_readable_source_map
from app.services.scanner.covers import cover_abs_path
from app.services.scanner.fsutil import safe_join

router = APIRouter(prefix="/books", tags=["books"])

_RANGE_CHUNK = 1024 * 1024


def _brief(book: Book) -> BookBrief:
    md = book.book_metadata
    return BookBrief(
        id=book.id,
        file_name=book.file_name,
        dir_path=book.dir_path,
        format=book.format,
        status=book.status,
        chapter_count=book.chapter_count,
        word_count=book.word_count,
        file_size=book.file_size,
        has_cover=bool(book.cover_path),
        cover_version=md.scraped_at.isoformat() if md and md.scraped_at else None,
        title=md.title if md else None,
        authors=md.authors if md else [],
    )


@router.get("", response_model=Page[BookBrief])
async def list_books(
    source_id: uuid.UUID | None = None,
    dir_path: str | None = None,
    format: BookFormat | None = None,
    q: str | None = Query(None, max_length=200),
    chapter_min: int | None = Query(None, ge=0),
    chapter_max: int | None = Query(None, ge=0),
    word_min: int | None = Query(None, ge=0),
    word_max: int | None = Query(None, ge=0),
    has_cover: bool | None = None,
    shelf: str | None = Query(None, pattern="^(my)$"),
    sort: str = Query("title", pattern="^(title|author|words|chapters|added|size|shelf_added)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    size: int = Query(24, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    source_map = await get_readable_source_map(db, user)
    # outerjoin 元数据:排序/筛选可能引用 title_sort/author_sort,且不排除无元数据的书
    base = (
        select(Book)
        .outerjoin(BookMetadata, BookMetadata.book_id == Book.id)
        .where(Book.status == BookStatus.active)
        .options(selectinload(Book.book_metadata))
    )
    base = apply_book_filter(base, user, source_map)
    # 书架过滤:shelf=my → 仅返回当前用户默认书架中的收藏
    # 用 join(ShelfBook) 而非子查询,便于 shelf_added 排序时引用 ShelfBook.added_at
    if shelf == "my":
        from app.services.shelf import get_or_create_default_shelf

        my_shelf = await get_or_create_default_shelf(db, user.id)
        base = base.join(ShelfBook, ShelfBook.book_id == Book.id).where(
            ShelfBook.shelf_id == my_shelf.id
        )
    if source_id:
        base = base.where(Book.source_id == source_id)
    if dir_path is not None:
        base = base.where(Book.dir_path == dir_path)
    if format:
        base = base.where(Book.format == format)
    # 关键字模糊匹配:文件名 + 元数据(标题/作者/描述/出版社/标签)
    # 作者/标签为 JSON 数组,序列化为文本后整体 LIKE,个人库量级足够
    if q and q.strip():
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                func.lower(Book.file_name).like(like.lower()),
                func.lower(BookMetadata.title).like(like.lower()),
                func.lower(BookMetadata.description).like(like.lower()),
                func.lower(BookMetadata.publisher).like(like.lower()),
                func.lower(cast(BookMetadata.authors, String)).like(like.lower()),
                func.lower(cast(BookMetadata.tags, String)).like(like.lower()),
            )
        )
    # 章节数范围
    if chapter_min is not None:
        base = base.where(Book.chapter_count >= chapter_min)
    if chapter_max is not None:
        base = base.where(Book.chapter_count <= chapter_max)
    # 字数范围(NULL 视为不满足范围条件,故显式要求 word_count 非空)
    if word_min is not None:
        base = base.where(Book.word_count.is_not(None), Book.word_count >= word_min)
    if word_max is not None:
        base = base.where(Book.word_count.is_not(None), Book.word_count <= word_max)
    # 是否有封面
    if has_cover is not None:
        base = base.where(Book.cover_path.is_not(None) if has_cover else Book.cover_path.is_(None))

    count_stmt = select(func.count()).select_from(base.order_by(None).subquery())
    total = await db.scalar(count_stmt) or 0

    ordered = base.order_by(*_order_clauses(sort, order))
    result = await db.execute(ordered.offset((page - 1) * size).limit(size))
    items = [_brief(b) for b in result.scalars().all()]
    return Page(items=items, total=total, page=page, size=size)


def _order_clauses(sort: str, order: str):
    """构造排序子句。NULL 值一律排到最后(nulls_last),末尾用稳定次键。"""
    desc = order == "desc"

    def d(col):
        return col.desc() if desc else col.asc()

    # 各排序字段对应主键列;字符串键用 collate NOCASE 保证大小写无关
    if sort == "author":
        primary = BookMetadata.author_sort
    elif sort == "words":
        primary = Book.word_count
    elif sort == "chapters":
        primary = Book.chapter_count
    elif sort == "added":
        primary = Book.added_at
    elif sort == "size":
        primary = Book.file_size
    elif sort == "shelf_added":
        # 需和 shelf=my join(ShelfBook) 配套使用;非 my 场景默认走 title
        primary = ShelfBook.added_at
    else:  # title
        primary = BookMetadata.title_sort

    # NULL 排最后:SQLite 支持 NULLS LAST 语法(3.30+)
    primary_clause = d(primary).nulls_last()
    # 稳定次键:目录 + 文件名,保证同值顺序确定
    return [primary_clause, Book.dir_path.asc(), Book.file_name.asc()]


@router.get("/tree", response_model=list[TreeNode])
async def book_tree(
    source_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """按文件夹层级返回目录树(受权限过滤,含每目录图书数)。"""
    source_map = await get_readable_source_map(db, user)
    stmt = select(Book.source_id, Book.dir_path, func.count().label("cnt")).where(
        Book.status == BookStatus.active
    )
    stmt = apply_book_filter(stmt, user, source_map)
    if source_id:
        stmt = stmt.where(Book.source_id == source_id)
    stmt = stmt.group_by(Book.source_id, Book.dir_path)
    rows = (await db.execute(stmt)).all()

    # 载入源名称
    src_result = await db.execute(select(Source))
    sources = {s.id: s for s in src_result.scalars().all()}

    return _build_tree(rows, sources)


async def _detail_response(db: AsyncSession, book: Book, user_id: uuid.UUID) -> BookDetail:
    md = await db.get(BookMetadata, book.id)
    prog = await _get_progress(db, user_id, book.id)
    return BookDetail(
        id=book.id,
        source_id=book.source_id,
        rel_path=book.rel_path,
        dir_path=book.dir_path,
        file_name=book.file_name,
        format=book.format,
        file_size=book.file_size,
        status=book.status,
        chapter_count=book.chapter_count,
        word_count=book.word_count,
        has_cover=bool(book.cover_path),
        double_page=book.double_page,
        start_right=book.start_right,
        added_at=book.added_at,
        metadata=MetadataOut.model_validate(md) if md else None,
        progress=ProgressOut.model_validate(prog) if prog else None,
    )


@router.get("/{book_id}", response_model=BookDetail)
async def book_detail(
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await _get_readable_book(db, user, book_id)
    return await _detail_response(db, book, user.id)


@router.get("/{book_id}/chapters", response_model=list[ChapterOut])
async def book_chapters(
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_readable_book(db, user, book_id)
    result = await db.execute(select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.idx))
    return list(result.scalars().all())


@router.get("/{book_id}/content", response_model=ChapterContent)
async def book_content(
    book_id: uuid.UUID,
    chapter_idx: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """读取指定章节的重排内容(txt/epub)。pdf 返回空 html,前端用文件流渲染。"""
    book = await _get_readable_book(db, user, book_id)
    result = await db.execute(select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.idx))
    chapters = list(result.scalars().all())
    if not chapters or chapter_idx >= len(chapters):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    ch = chapters[chapter_idx]
    next_loc = chapters[chapter_idx + 1].location if chapter_idx + 1 < len(chapters) else None

    html = ""
    if book.format != BookFormat.pdf:
        abs_path = await _abs_path(db, book)
        parser = get_parser(book.format.value)
        if parser and abs_path:
            from app.services.parsers.base import ParsedChapter

            html = parser.read_chapter(
                abs_path, ParsedChapter(idx=ch.idx, title=ch.title, location=ch.location), next_loc
            )
    return ChapterContent(idx=ch.idx, title=ch.title, location=ch.location, html=html)


@router.get("/{book_id}/comic_image")
async def book_comic_image(
    book_id: uuid.UUID,
    chapter_idx: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """漫画单章图片二进制流(替代 base64 内嵌,支持浏览器缓存与预加载)。"""
    book = await _get_readable_book(db, user, book_id)
    if book.format != BookFormat.comic:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非漫画书籍")
    result = await db.execute(select(Chapter).where(Chapter.book_id == book_id).order_by(Chapter.idx))
    chapters = list(result.scalars().all())
    if not chapters or chapter_idx >= len(chapters):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="章节不存在")
    ch = chapters[chapter_idx]
    abs_path = await _abs_path(db, book)
    if not abs_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    from app.services.parsers.comic import get_chapter_image

    raw, mime = get_chapter_image(abs_path, ch.location)
    if not raw:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图片加载失败")
    # 图片内容随文件内容固定,可长缓存;book_id+chapter 唯一确定图片
    return Response(content=raw, media_type=mime, headers={"Cache-Control": "private, max-age=86400"})


@router.get("/{book_id}/file")
async def book_file(
    book_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """原始文件流(pdf/epub 前端渲染用),支持 Range 断点续传。"""
    book = await _get_readable_book(db, user, book_id)
    abs_path = await _abs_path(db, book)
    if not abs_path or not os.path.isfile(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return _ranged_file_response(abs_path, request, book.file_name)


@router.get("/{book_id}/cover")
async def book_cover(
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await _get_readable_book(db, user, book_id)
    if not book.cover_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="无封面")
    path = cover_abs_path(book.cover_path)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="封面文件不存在")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{book_id}/progress", response_model=ProgressOut)
async def get_progress(
    book_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_readable_book(db, user, book_id)
    prog = await _get_progress(db, user.id, book_id)
    return ProgressOut.model_validate(prog) if prog else ProgressOut()


@router.put("/{book_id}/progress", response_model=ProgressOut)
async def put_progress(
    book_id: uuid.UUID,
    payload: ProgressUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_readable_book(db, user, book_id)
    prog = await _get_progress(db, user.id, book_id)
    if prog is None:
        prog = ReadingProgress(user_id=user.id, book_id=book_id)
        db.add(prog)
    prog.location = payload.location
    prog.percent = payload.percent
    prog.chapter_idx = payload.chapter_idx
    await db.commit()
    await db.refresh(prog)
    return ProgressOut.model_validate(prog)


@router.put("/{book_id}/comic_settings", response_model=BookDetail)
async def update_comic_settings(
    book_id: uuid.UUID,
    payload: BookComicSettingsUpdate,  # type: ignore
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    book = await _get_readable_book(db, user, book_id)
    if payload.double_page is not None:
        book.double_page = payload.double_page
    if payload.start_right is not None:
        book.start_right = payload.start_right
    await db.commit()
    await db.refresh(book)
    return await _detail_response(db, book, user.id)


# ---------- 内部辅助 ----------
async def _get_readable_book(db: AsyncSession, user: User, book_id: uuid.UUID) -> Book:
    book = await db.get(Book, book_id, options=[selectinload(Book.book_metadata)])
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="图书不存在")
    if not await can_read_book(db, user, book):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该图书")
    return book


async def _get_progress(db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID):
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user_id, ReadingProgress.book_id == book_id
        )
    )
    return result.scalar_one_or_none()


async def _abs_path(db: AsyncSession, book: Book) -> str | None:
    source = await db.get(Source, book.source_id)
    if source is None:
        return None
    return safe_join(source.root_path, book.rel_path)


def _build_tree(rows, sources) -> list[TreeNode]:
    """把 (source_id, dir_path, count) 扁平行构建为按源分组的目录树。"""
    roots: dict[uuid.UUID, TreeNode] = {}
    nodes: dict[tuple[uuid.UUID, str], TreeNode] = {}

    def ensure_node(source_id: uuid.UUID, path: str) -> TreeNode:
        key = (source_id, path)
        if key in nodes:
            return nodes[key]
        name = os.path.basename(path) if path else (sources[source_id].name if source_id in sources else "")
        node = TreeNode(name=name, path=path, source_id=source_id)
        nodes[key] = node
        if not path:
            roots[source_id] = node
        else:
            parent_path = os.path.dirname(path)
            parent = ensure_node(source_id, parent_path)
            parent.children.append(node)
        return node

    for source_id, dir_path, cnt in rows:
        if source_id not in sources:
            continue
        node = ensure_node(source_id, dir_path or "")
        node.book_count += cnt

    return list(roots.values())


def _ranged_file_response(path: str, request: Request, filename: str) -> Response:
    """支持 HTTP Range 的文件响应(pdf.js/epubjs 分段加载)。"""
    file_size = os.path.getsize(path)
    range_header = request.headers.get("range")
    if range_header is None:
        return FileResponse(path, filename=filename)

    try:
        unit, _, rng = range_header.partition("=")
        start_s, _, end_s = rng.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return FileResponse(path, filename=filename)
    end = min(end, file_size - 1)
    length = end - start + 1

    def iterfile():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(_RANGE_CHUNK, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    return StreamingResponse(
        iterfile(), status_code=status.HTTP_206_PARTIAL_CONTENT, headers=headers,
        media_type="application/octet-stream",
    )
