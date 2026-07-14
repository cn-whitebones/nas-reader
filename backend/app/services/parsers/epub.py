"""EPUB 格式解析器:用 ebooklib 读取 TOC、封面、章节 HTML。"""
from __future__ import annotations

import warnings

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter

# ebooklib 会对未来版本弃用发出噪音警告,静默
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib")
warnings.filterwarnings("ignore", category=FutureWarning, module="ebooklib")


class EpubParser(BaseParser):
    extensions = ("epub",)

    def parse(self, file_path: str) -> ParsedBook:
        try:
            import ebooklib
            from ebooklib import epub
        except Exception:
            return ParsedBook()

        try:
            book = epub.read_epub(file_path)
        except Exception:
            return ParsedBook()

        result = ParsedBook()

        # 元数据
        try:
            titles = book.get_metadata("DC", "title")
            if titles:
                result.title = titles[0][0]
            creators = book.get_metadata("DC", "creator")
            result.authors = [c[0] for c in creators] if creators else []
            langs = book.get_metadata("DC", "language")
            if langs:
                result.language = langs[0][0]
        except Exception:
            pass

        # 封面
        result.cover_bytes = self._extract_cover(book, ebooklib)

        # 章节:优先用 TOC,其次用 spine 顺序
        chapters = self._chapters_from_toc(book)
        if not chapters:
            chapters = self._chapters_from_spine(book)
        result.chapters = chapters
        return result

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        try:
            from ebooklib import epub
        except Exception:
            return ""
        try:
            book = epub.read_epub(file_path)
        except Exception:
            return ""
        # location 形如 "path/to/chapter.xhtml" 或含锚点 "chap.xhtml#frag"
        href = chapter.location.split("#", 1)[0]
        item = book.get_item_with_href(href)
        if item is None:
            return ""
        try:
            html = item.get_content().decode("utf-8", errors="replace")
        except Exception:
            return ""

        from app.services.parsers.base import clean_html_body
        return clean_html_body(html)

    # ---------- 内部 ----------
    def _extract_cover(self, book, ebooklib) -> bytes | None:
        try:
            covers = list(book.get_items_of_type(ebooklib.ITEM_COVER))
            if covers:
                return covers[0].get_content()
            # 回退:找名字含 cover 的图片
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                if "cover" in item.get_name().lower():
                    return item.get_content()
        except Exception:
            pass
        return None

    def _chapters_from_toc(self, book) -> list[ParsedChapter]:
        chapters: list[ParsedChapter] = []

        def walk(entries):
            for entry in entries:
                if isinstance(entry, tuple):
                    # (Section, [children]) 或 (Link, [children])
                    section, children = entry
                    _append(section)
                    walk(children)
                else:
                    _append(entry)

        def _append(link):
            href = getattr(link, "href", None)
            title = getattr(link, "title", None)
            if href:
                chapters.append(
                    ParsedChapter(idx=len(chapters), title=(title or "").strip()[:120], location=href)
                )

        try:
            walk(book.toc)
        except Exception:
            return []
        return chapters

    def _chapters_from_spine(self, book) -> list[ParsedChapter]:
        chapters: list[ParsedChapter] = []
        try:
            for spine_id, _ in book.spine:
                item = book.get_item_with_id(spine_id)
                if item is None:
                    continue
                chapters.append(
                    ParsedChapter(
                        idx=len(chapters),
                        title=f"第 {len(chapters) + 1} 节",
                        location=item.get_name(),
                    )
                )
        except Exception:
            pass
        return chapters
