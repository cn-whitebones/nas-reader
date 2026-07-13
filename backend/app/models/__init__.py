"""集中导入全部 ORM 模型,供 Alembic autogenerate 与运行时使用。"""
from app.models.book import Book, BookFormat, BookMetadata, Chapter, MetadataProviderName  # noqa: F401
from app.models.reading import (  # noqa: F401
    ReadingProgress,
    ReadingSettings,
    Shelf,
    ShelfBook,
)
from app.models.source import ScanStatus, ScanTask, Source, SourceType  # noqa: F401
from app.models.user import Permission, User, UserRole  # noqa: F401
