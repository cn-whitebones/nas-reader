"""封面存储:把提取的封面字节落盘并生成缩略图,返回相对路径。"""
from __future__ import annotations

import io
from pathlib import Path

from app.core.config import settings

_THUMB_MAX = (400, 600)  # 缩略图最大宽高


def save_cover(book_id: str, cover_bytes: bytes) -> str | None:
    """保存封面缩略图到 cover_dir/<book_id>.jpg,返回文件名。失败返回 None。"""
    if not cover_bytes:
        return None
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(cover_bytes))
        img = img.convert("RGB")
        img.thumbnail(_THUMB_MAX)
        out_dir = Path(settings.cover_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{book_id}.jpg"
        img.save(out_dir / filename, format="JPEG", quality=82)
        return filename
    except Exception:
        return None


def cover_abs_path(filename: str) -> Path:
    return Path(settings.cover_dir) / filename
