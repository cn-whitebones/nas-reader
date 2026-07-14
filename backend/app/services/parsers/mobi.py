"""MOBI 格式解析器:用 mobi 库提取目录、封面和内容。

MOBI 内部是 Palm DB 格式,章节按偏移定位,和 txt 类似。
注意:KF8(Kindle Format 8) 解压后会得到 epub 文件,需委托 EpubParser。
"""
from __future__ import annotations

import os
from pathlib import Path

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter


class MobiParser(BaseParser):
    extensions = ("mobi", "azw", "azw3")

    def __init__(self):
        # KF8 格式解压后得到 epub,委托 EpubParser
        self._epub_parser = None

    def _get_epub_parser(self):
        if self._epub_parser is None:
            from app.services.parsers.epub import EpubParser
            self._epub_parser = EpubParser()
        return self._epub_parser

    def parse(self, file_path: str) -> ParsedBook:
        try:
            import mobi
        except Exception:
            return ParsedBook()

        try:
            headers, output = mobi.extract(file_path)
        except Exception:
            return ParsedBook()

        # KF8 格式: mobi.extract 直接返回 epub 文件路径,直接走 EpubParser
        if output.lower().endswith(".epub") and os.path.isfile(output):
            return self._get_epub_parser().parse(output)

        # 传统 MOBI7 格式:按字符偏移解析
        result = ParsedBook()

        # 元数据(从 headers dict 提取)
        try:
            result.title = headers.get("title") or Path(file_path).stem
            authors = headers.get("author")
            if authors:
                result.authors = [str(authors)] if isinstance(authors, str) else list(authors)
            result.language = headers.get("language")
        except Exception:
            pass

        # 章节:mobi 目录结构在 headers.get("toc", []),每项含 (title, offset)
        try:
            toc = headers.get("toc", [])
            chapters: list[ParsedChapter] = []
            for entry in toc:
                if isinstance(entry, dict):
                    title = str(entry.get("title", "") or "")
                    offset = entry.get("offset", 0)
                elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                    title = str(entry[0] or "")
                    offset = entry[1] if isinstance(entry[1], int) else 0
                else:
                    continue
                if title or offset:
                    chapters.append(
                        ParsedChapter(
                            idx=len(chapters),
                            title=(title.strip() or f"第 {len(chapters) + 1} 节")[:120],
                            location=str(offset),
                        )
                    )
            result.chapters = chapters
        except Exception:
            pass

        # TOC 无效 → 单章
        if not result.chapters:
            result.chapters = [ParsedChapter(idx=0, title="全文", location="0")]

        return result

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        try:
            import mobi
        except Exception:
            return ""

        try:
            headers, output = mobi.extract(file_path)
        except Exception:
            return ""

        # KF8 格式: output 本身就是 epub 文件路径
        if output.lower().endswith(".epub") and os.path.isfile(output):
            return self._get_epub_parser().read_chapter(output, chapter, next_location)

        # 传统 MOBI7: output 可能是 .html 文件本身,也可能是目录
        if output.lower().endswith(".html") or output.lower().endswith(".htm"):
            html_file = output
        elif os.path.isdir(output):
            html_file = os.path.join(output, "book.html")
            if not os.path.exists(html_file):
                for name in os.listdir(output):
                    if name.lower().endswith(".html") or name.lower().endswith(".htm"):
                        html_file = os.path.join(output, name)
                        break
                else:
                    return ""
        else:
            return ""

        try:
            with open(html_file, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            return ""

        # 按偏移截取
        try:
            start = int(chapter.location) if chapter.location.lstrip("-").isdigit() else 0
            end = int(next_location) if next_location and next_location.lstrip("-").isdigit() else len(text)
        except ValueError:
            start = 0
            end = len(text)

        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))

        from app.services.parsers.base import clean_html_body
        return clean_html_body(text[start:end])
