"""漫画压缩包解析器:zip/cbz/rar/cbr,章节 = 按文件名排序的图片。

漫画和文本格式差异很大:每"章"实际是一张图片。read_chapter 返回
带 base64 内嵌图片的 HTML,供阅读器统一渲染。
"""
from __future__ import annotations

import imghdr
import zipfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter

# 支持的图片扩展名
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
# 压缩包扩展名
_ARCHIVE_EXTS = {"zip", "cbz", "rar", "cbr", "7z", "cb7"}


def _is_image(name: str) -> bool:
    return Path(name).suffix.lower() in _IMAGE_EXTS


def _natural_sort_key(name: str) -> list:
    """文件名自然排序:01.jpg < 2.jpg < 10.jpg,兼容中文/数字混合。"""
    import re
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


@lru_cache(maxsize=4)
def _get_zip_list(file_path: str) -> list[tuple[str, int, int]]:
    """返回压缩包内图片列表(按文件名自然排序) + CRC32 + 文件大小。

    带 LRU 缓存,避免同一文件反复打开 zip 列目录。(CRC,size)用于验证文件未变。
    """
    result: list[tuple[str, int, int]] = []
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            for info in zf.infolist():
                if not info.is_dir() and _is_image(info.filename):
                    result.append((info.filename, info.CRC, info.file_size))
        result.sort(key=lambda t: _natural_sort_key(t[0]))
    except Exception:
        pass
    return result


@lru_cache(maxsize=4)
def _read_zip_image(file_path: str, image_path: str) -> bytes:
    """读取压缩包内一张图的原始字节,带 LRU 缓存。"""
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            return zf.read(image_path)
    except Exception:
        return b""


def get_chapter_image(file_path: str, image_path: str) -> tuple[bytes, str]:
    """读取压缩包内某张图,做尺寸标准化,返回 (原始字节, MIME)。

    供漫画图片二进制接口与旧 base64 HTML 接口共用。读不到返回 (b"", "")。
    """
    raw = _read_zip_image(file_path, image_path)
    if not raw:
        return b"", ""

    # 用 Pillow 推断 MIME(比后缀可靠),并对超宽图做限宽
    img_format = None
    try:
        with Image.open(BytesIO(raw)) as img:
            img_format = img.format
            max_w = 2560
            if img.width > max_w:
                ratio = max_w / img.width
                new_h = int(img.height * ratio)
                img = img.resize((max_w, new_h), Image.Resampling.LANCZOS)
                buf = BytesIO()
                fmt = "JPEG" if img_format in ("JPEG", None) else "PNG"
                img.save(buf, format=fmt, quality=85, optimize=True)
                raw = buf.getvalue()
                img_format = fmt
    except Exception:
        pass

    mime = "image/jpeg"
    if img_format == "PNG":
        mime = "image/png"
    elif img_format in ("GIF", "WEBP", "BMP"):
        mime = f"image/{img_format.lower()}"
    else:
        what = imghdr.what(None, h=raw[:512])
        if what in ("png", "gif", "webp", "bmp"):
            mime = f"image/{what}"
    return raw, mime


class ComicParser(BaseParser):
    extensions = tuple(_ARCHIVE_EXTS)

    def parse(self, file_path: str) -> ParsedBook:
        images = _get_zip_list(file_path)
        chapters = [
            ParsedChapter(idx=i, title=Path(name).name[:120], location=name)
            for i, (name, _, _) in enumerate(images)
        ]

        # 封面 = 第一张图
        cover_bytes = None
        if images:
            try:
                cover_bytes = _read_zip_image(file_path, images[0][0])
            except Exception:
                pass

        # 书名从文件名来,压缩包无内嵌元数据
        title = Path(file_path).stem
        return ParsedBook(chapters=chapters, cover_bytes=cover_bytes, title=title)

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        """漫画章节 = 单张图片,返回 base64 内嵌 <img> HTML。

        (保留:兼容旧的统一 content 接口。漫画阅读现优先走 comic_image 二进制接口。)
        """
        raw, mime = get_chapter_image(file_path, chapter.location)
        if not raw:
            return '<p>图片加载失败</p>'

        import base64
        b64 = base64.b64encode(raw).decode("ascii")

        # 居中显示,max-width 限制宽度,height auto 保持比例
        return f'<div style="text-align:center"><img style="max-width:100%;height:auto;display:block;margin:0 auto" src="data:{mime};base64,{b64}" alt="{Path(chapter.location).name}" /></div>'
