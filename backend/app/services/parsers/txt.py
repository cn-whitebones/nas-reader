"""TXT 格式解析器:按章节标题正则提取章节,按字符偏移定位。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter

# 常见章节标题: 第X章 / 第X节 / Chapter X / 序言 / 楔子 / 卷 / 部
_CHAPTER_RE = re.compile(
    r"^\s*(?:第\s*[0-9零一二三四五六七八九十百千两]+\s*[章节回卷篇部集]"
    r"|Chapter\s+\d+"
    r"|楔子|序章|序言|前言|引子|尾声|后记|番外|附录)"
    r".{0,40}$",
    re.IGNORECASE,
)
_MAX_TITLE_LEN = 60
_FALLBACK_CHUNK = 5000  # 无章节时按此字符数分块


@lru_cache(maxsize=8)
def _read_text(file_path: str) -> str:
    """读取整篇文本(带小缓存,避免同一文件反复读盘)。"""
    try:
        return Path(file_path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


class TxtParser(BaseParser):
    extensions = ("txt", "text")

    def parse(self, file_path: str) -> ParsedBook:
        text = _read_text(file_path)
        chapters: list[ParsedChapter] = []
        offset = 0
        for line in text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped and len(stripped) <= _MAX_TITLE_LEN and _CHAPTER_RE.match(stripped):
                chapters.append(
                    ParsedChapter(idx=len(chapters), title=stripped[:120], location=str(offset))
                )
            offset += len(line)

        if not chapters:
            # 无标准章节标题 → 按固定字符数分块
            for i in range(0, max(len(text), 1), _FALLBACK_CHUNK):
                chunk_head = text[i : i + 40].strip().splitlines()
                title = (chunk_head[0][:40] if chunk_head else "") or f"第 {i // _FALLBACK_CHUNK + 1} 节"
                chapters.append(ParsedChapter(idx=len(chapters), title=title, location=str(i)))
        return ParsedBook(chapters=chapters)

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        text = _read_text(file_path)
        start = int(chapter.location) if chapter.location.lstrip("-").isdigit() else 0
        end = int(next_location) if next_location and next_location.lstrip("-").isdigit() else len(text)
        chunk = text[start:end]
        # 转 HTML 段落,首行作为标题
        parts = [p.strip() for p in chunk.replace("\r\n", "\n").split("\n")]
        return "".join(f"<p>{_escape(p)}</p>" for p in parts if p)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
