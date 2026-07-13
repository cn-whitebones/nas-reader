"""PDF 格式解析器:用 PyMuPDF(fitz) 提取 TOC 与首页封面。

阅读时 PDF 由前端 pdf.js 直接渲染原文件,故 read_chapter 返回空。
"""
from __future__ import annotations

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter


class PdfParser(BaseParser):
    extensions = ("pdf",)

    def parse(self, file_path: str) -> ParsedBook:
        try:
            import fitz  # PyMuPDF
        except Exception:
            return ParsedBook()

        try:
            doc = fitz.open(file_path)
        except Exception:
            return ParsedBook()

        result = ParsedBook()
        try:
            meta = doc.metadata or {}
            result.title = meta.get("title") or None
            author = meta.get("author")
            result.authors = [author] if author else []

            # 章节:PDF 书签(TOC)。location 存目标页码(从 1 开始)
            toc = doc.get_toc(simple=True)  # [[level, title, page], ...]
            chapters: list[ParsedChapter] = []
            for _level, title, page in toc:
                chapters.append(
                    ParsedChapter(idx=len(chapters), title=(title or "").strip()[:120], location=str(page))
                )
            if not chapters:
                # 无书签 → 每页一章的降级方案代价高,改为按页码分段(每 20 页一节)
                total = doc.page_count
                step = 20 if total > 40 else max(total, 1)
                for start in range(0, total, step):
                    chapters.append(
                        ParsedChapter(
                            idx=len(chapters),
                            title=f"第 {start + 1}-{min(start + step, total)} 页",
                            location=str(start + 1),
                        )
                    )
            result.chapters = chapters

            # 封面:渲染首页为 PNG
            if doc.page_count > 0:
                page = doc.load_page(0)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                result.cover_bytes = pix.tobytes("png")
        except Exception:
            pass
        finally:
            doc.close()
        return result

    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        # PDF 由前端 pdf.js 渲染,不提供 HTML 正文
        return ""
