"""书籍查询共享工具:排序、搜索过滤等通用逻辑。

抽取重复代码到此处，供多个端点复用。
"""
from sqlalchemy import Select, func, or_, cast, String
from sqlalchemy.orm import aliased

from app.models.book import Book, BookMetadata
from app.models.reading import ShelfBook


def apply_keyword_filter(stmt: Select, q: str | None) -> Select:
    """应用关键词模糊搜索过滤。

    搜索范围: 文件名、标题、描述、出版社、作者、标签
    大小写不敏感匹配。
    """
    if not q or not q.strip():
        return stmt

    like = f"%{q.strip()}%"
    stmt = stmt.where(
        or_(
            func.lower(Book.file_name).like(like.lower()),
            func.lower(BookMetadata.title).like(like.lower()),
            func.lower(BookMetadata.description).like(like.lower()),
            func.lower(BookMetadata.publisher).like(like.lower()),
            func.lower(cast(BookMetadata.authors, String)).like(like.lower()),
            func.lower(cast(BookMetadata.tags, String)).like(like.lower()),
        )
    )
    return stmt


def get_order_clauses(sort: str, order: str):
    """构造排序子句。

    规则:
    - NULL 值一律排到最后 (nulls_last)
    - 末尾添加稳定次键 (dir_path + file_name) 保证顺序确定
    - 排序字段支持: title, author, words, chapters, added, size, shelf_added

    对于 'shelf_added' 排序，需要查询已联join ShelfBook，调用方确保这一点。
    """
    desc = order == "desc"

    def _d(col):
        clause = col.desc() if desc else col.asc()
        return clause.nulls_last()

    # 各排序字段对应主键列
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
        primary = ShelfBook.added_at
    else:  # title
        primary = BookMetadata.title_sort

    # NULL 排最后，稳定次键:目录 + 文件名
    return [_d(primary), Book.dir_path.asc(), Book.file_name.asc()]
