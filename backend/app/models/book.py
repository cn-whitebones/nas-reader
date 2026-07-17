"""ORM 模型:图书、元数据、章节。"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BookFormat(str, enum.Enum):
    txt = "txt"
    epub = "epub"
    pdf = "pdf"
    mobi = "mobi"
    comic = "comic"


class BookStatus(str, enum.Enum):
    active = "active"
    missing = "missing"  # 磁盘文件已不存在,但保留记录与进度


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        UniqueConstraint("source_id", "rel_path", name="uq_book_source_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    rel_path: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    dir_path: Mapped[str] = mapped_column(String(2048), default="", index=True)  # 所在目录(相对),按层级展示用
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    format: Mapped[BookFormat] = mapped_column(Enum(BookFormat), nullable=False, index=True)
    file_hash: Mapped[str] = mapped_column(String(64), index=True)  # xxhash(首段)+size,稳定标识
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)
    cover_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[BookStatus] = mapped_column(Enum(BookStatus), default=BookStatus.active, index=True)
    chapter_count: Mapped[int] = mapped_column(Integer, default=0)
    # 字数:txt/epub/mobi 精确统计;pdf/漫画无法可靠统计,保持 NULL
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source: Mapped["Source"] = relationship(back_populates="books")  # noqa: F821
    book_metadata: Mapped["BookMetadata | None"] = relationship(
        back_populates="book", cascade="all, delete-orphan", uselist=False
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", order_by="Chapter.idx"
    )


class MetadataProviderName(str, enum.Enum):
    douban = "douban"
    google = "google"
    openlibrary = "openlibrary"
    manual = "manual"


class BookMetadata(Base):
    __tablename__ = "book_metadata"

    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    title: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    subtitle: Mapped[str | None] = mapped_column(String(512), nullable=True)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    # 拼音排序键(小写):中文书名/作者按拼音排序用,入库时生成,index 便于排序分页
    title_sort: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    author_sort: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    publisher: Mapped[str | None] = mapped_column(String(256), nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    pub_date: Mapped[date | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    douban_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_provider: Mapped[MetadataProviderName | None] = mapped_column(
        Enum(MetadataProviderName), nullable=True
    )
    scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    book: Mapped["Book"] = relationship(back_populates="book_metadata")


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "idx", name="uq_chapter_book_idx"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("books.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)  # 从 0 开始的顺序
    title: Mapped[str] = mapped_column(String(512), default="")
    # 格式相关定位:pdf=页码, epub=href(可含锚点), txt=字符偏移
    location: Mapped[str] = mapped_column(String(1024), default="")

    book: Mapped["Book"] = relationship(back_populates="chapters")
