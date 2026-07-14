"""MOBI 格式解析器:用 mobi 库提取目录、封面和内容。

MOBI 内部是 Palm DB 格式,章节按偏移定位,和 txt 类似。
"""
from __future__ import annotations

from pathlib import Path

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter


class MobiParser(BaseParser):
    extensions = ("mobi", "azw", "azw3")

    def parse(self, file_path: str) -> ParsedBook:
        try:
            import mobi
        except Exception:
            return ParsedBook()

        try:
            # mobi.extract 返回 (headers, html_path)
            headers, _ = mobi.extract(file_path)
        except Exception:
            return ParsedBook()

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

        # 封面:mobi 库提取时可能在输出目录里有 cover.jpg,但 mobi.extract 本身
        # 不直接返回字节,后续可扩展(临时目录找 cover)。暂不提取封面。

        # 章节:mobi 目录结构在 headers.get("toc", []),每项含 (title, offset)
        # 注意:不同 mobi 版本的 TOC 格式可能不同,兼容失败时退化为不分章
        try:
            toc = headers.get("toc", [])
            chapters: list[ParsedChapter] = []
            for entry in toc:
                # entry 可能是 dict 或 tuple,兼容常见格式
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

        # TOC 无效或为空 → 退化为单章整本书
        if not result.chapters:
            result.chapters = [ParsedChapter(idx=0, title="全文", location="0")]

        return result

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        """读取章节内容:mobi 文本按字符偏移分段。

        注意:mobi.extract 会把整本书转成单个 HTML,chapter.location 是字符偏移。
        """
        try:
            import mobi
        except Exception:
            return ""

        try:
            _, html_path = mobi.extract(file_path)
            with open(html_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception:
            return ""

        # 解析偏移
        try:
            start = int(chapter.location) if chapter.location.lstrip("-").isdigit() else 0
            end = int(next_location) if next_location and next_location.lstrip("-").isdigit() else len(text)
        except ValueError:
            start = 0
            end = len(text)

        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))

        # 直接返回 HTML(已经是 mobi 转出来的 XHTML)
        return text[start:end]
