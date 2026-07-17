"""Pydantic schemas:图书、元数据、章节、目录树、进度、阅读设置、书架。"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.book import BookFormat, BookStatus, MetadataProviderName


# ---------- 元数据 ----------
class MetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] = []
    publisher: str | None = None
    isbn: str | None = None
    pub_date: date | None = None
    description: str | None = None
    language: str | None = None
    tags: list[str] = []
    rating: float | None = None
    douban_id: str | None = None
    source_provider: MetadataProviderName | None = None


class MetadataUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    authors: list[str] | None = None
    publisher: str | None = None
    isbn: str | None = None
    pub_date: date | None = None
    description: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    rating: float | None = None


# ---------- 章节 ----------
class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    idx: int
    title: str
    location: str


# ---------- 进度 ----------
class ProgressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    location: str = ""
    percent: float = 0.0
    chapter_idx: int = 0
    updated_at: datetime | None = None


class ProgressUpdate(BaseModel):
    location: str = ""
    percent: float = Field(default=0.0, ge=0, le=100)
    chapter_idx: int = 0


# ---------- 图书 ----------
class BookBrief(BaseModel):
    """列表用精简视图。"""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    file_name: str
    dir_path: str
    format: BookFormat
    status: BookStatus
    chapter_count: int
    word_count: int | None = None
    file_size: int = 0
    has_cover: bool = False
    title: str | None = None
    authors: list[str] = []


class BookDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID
    rel_path: str
    dir_path: str
    file_name: str
    format: BookFormat
    file_size: int
    status: BookStatus
    chapter_count: int
    word_count: int | None = None
    has_cover: bool = False
    added_at: datetime
    metadata: MetadataOut | None = None
    progress: ProgressOut | None = None


# ---------- 目录树 ----------
class TreeNode(BaseModel):
    name: str
    path: str  # 相对源根的目录路径
    source_id: uuid.UUID
    book_count: int = 0
    children: list["TreeNode"] = []


# ---------- 阅读内容 ----------
class ChapterContent(BaseModel):
    idx: int
    title: str
    location: str
    html: str  # txt/epub 重排内容;pdf 为空(前端直接渲染文件)


# ---------- 阅读设置 ----------
class ReadingSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    font_family: str
    font_size: int
    line_height: float
    margin: int
    theme: str
    extra: dict = {}


class ReadingSettingsUpdate(BaseModel):
    font_family: str | None = None
    font_size: int | None = Field(default=None, ge=8, le=48)
    line_height: float | None = Field(default=None, ge=1.0, le=3.0)
    margin: int | None = Field(default=None, ge=0, le=100)
    theme: str | None = None
    extra: dict | None = None


# ---------- 书架 ----------
class ShelfCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    sort_order: int = 0


class ShelfUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    sort_order: int | None = None


class ShelfOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    sort_order: int
    book_count: int = 0
    created_at: datetime


class ShelfBookAdd(BaseModel):
    book_id: uuid.UUID
