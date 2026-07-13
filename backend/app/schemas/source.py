"""Pydantic schemas:文件源、扫描任务。"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.source import ScanStatus, SourceType


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    root_path: str = Field(min_length=1, max_length=1024)
    type: SourceType = SourceType.book
    auto_scan: bool = False
    scan_interval_minutes: int = Field(default=60, ge=1, le=1440)


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    type: SourceType | None = None
    auto_scan: bool | None = None
    scan_interval_minutes: int | None = Field(default=None, ge=1, le=1440)
    enabled: bool | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    root_path: str
    type: SourceType
    auto_scan: bool
    scan_interval_minutes: int
    enabled: bool
    last_scan_at: datetime | None
    created_at: datetime


class ScanTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    source_id: uuid.UUID
    status: ScanStatus
    total: int
    processed: int
    added: int
    updated: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
