"""MOBI 格式解析器:用 mobi 库解压后提取目录、封面和内容。

关键约定(容易踩坑):`mobi.extract(path)` 返回的是 **(tempdir, output_file)**,
第一个返回值是解压临时目录的路径字符串,**不是** headers/元数据字典。
早期实现把它当 dict 调 `.get("toc")`,必然抛异常并被吞掉,导致所有 MOBI7
书籍都只识别出「全文」一章、元数据也全丢。

两种内部格式:
  - KF8 (azw3 及新版 mobi):output 是 .epub,直接委托 EpubParser。
  - 传统 MOBI7:output 是 book.html,同目录下有 toc.ncx(标准 NCX 目录)与
    content.opf。章节锚点写作 `<a id="filepkeyN" />`,NCX 的
    `content src="book.html#fileposN"` 通过该 id 定位到 html 中的字符偏移。
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from app.services.parsers.base import (
    BaseParser,
    ParsedBook,
    ParsedChapter,
    clean_html_body,
)

_NCX_NS = "{http://www.daisy.org/z3986/2005/ncx/}"


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

    # ---------- parse ----------
    def parse(self, file_path: str) -> ParsedBook:
        try:
            import mobi
        except Exception:
            return ParsedBook()

        try:
            _tempdir, output = mobi.extract(file_path)
        except Exception:
            return ParsedBook()

        # KF8 格式:mobi.extract 返回 epub 文件路径,直接走 EpubParser
        if output.lower().endswith(".epub") and os.path.isfile(output):
            return self._get_epub_parser().parse(output)

        # 传统 MOBI7:output 是 book.html
        result = ParsedBook()
        html = self._read_html(output)
        html_dir = os.path.dirname(output)

        # 元数据 & 封面来自 content.opf
        self._fill_from_opf(result, html_dir, file_path)

        # 章节来自 toc.ncx,锚点 id 定位字符偏移
        result.chapters = self._chapters_from_ncx(html_dir, html)

        # NCX 无效 → 单章兜底
        if not result.chapters:
            result.chapters = [ParsedChapter(idx=0, title="全文", location="0")]

        return result

    # ---------- read_chapter ----------
    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        try:
            import mobi
        except Exception:
            return ""

        try:
            _tempdir, output = mobi.extract(file_path)
        except Exception:
            return ""

        # KF8 格式:output 本身就是 epub 文件路径
        if output.lower().endswith(".epub") and os.path.isfile(output):
            return self._get_epub_parser().read_chapter(output, chapter, next_location)

        # 传统 MOBI7:按字符偏移截取 book.html
        text = self._read_html(output)
        if not text:
            return ""

        start = int(chapter.location) if chapter.location.lstrip("-").isdigit() else 0
        end = (
            int(next_location)
            if next_location and next_location.lstrip("-").isdigit()
            else len(text)
        )
        start = max(0, min(start, len(text)))
        end = max(start, min(end, len(text)))
        return clean_html_body(text[start:end])

    # ---------- 内部 ----------
    @staticmethod
    def _read_html(output: str) -> str:
        """读取 MOBI7 解压出的 book.html。output 可能是 .html 文件或其所在目录。"""
        html_file = ""
        if output.lower().endswith((".html", ".htm")) and os.path.isfile(output):
            html_file = output
        elif os.path.isdir(output):
            cand = os.path.join(output, "book.html")
            if os.path.isfile(cand):
                html_file = cand
            else:
                for name in os.listdir(output):
                    if name.lower().endswith((".html", ".htm")):
                        html_file = os.path.join(output, name)
                        break
        if not html_file:
            return ""
        try:
            with open(html_file, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""

    def _chapters_from_ncx(self, html_dir: str, html: str) -> list[ParsedChapter]:
        """解析同目录 toc.ncx,用 navPoint 的 fragment 作为 html id 锚点定位字符偏移。"""
        ncx_path = self._find_file(html_dir, ".ncx")
        if not ncx_path or not html:
            return []
        try:
            tree = ET.parse(ncx_path)
        except Exception:
            return []

        chapters: list[ParsedChapter] = []
        for np in tree.iter(f"{_NCX_NS}navPoint"):
            label = np.find(f".//{_NCX_NS}text")
            content = np.find(f"{_NCX_NS}content")
            if label is None or content is None:
                continue
            title = (label.text or "").strip()
            src = content.get("src", "")
            frag = src.split("#", 1)[1] if "#" in src else ""
            offset = 0
            if frag:
                # 锚点写作 <a id="fileposN" />;定位到该标签结束 '>' 之后,
                # 避免切片时把锚点标签残片带进正文开头
                m = re.search(rf'<[^>]*id=[\'"]{re.escape(frag)}[\'"][^>]*>', html)
                if m:
                    offset = m.end()
                else:
                    m = re.search(rf'id=[\'"]{re.escape(frag)}[\'"]', html)
                    if m:
                        offset = m.start()
            chapters.append(
                ParsedChapter(
                    idx=len(chapters),
                    title=(title or f"第 {len(chapters) + 1} 节")[:120],
                    location=str(offset),
                )
            )
        return chapters

    def _fill_from_opf(self, result: ParsedBook, html_dir: str, file_path: str) -> None:
        """从 content.opf 提取标题/作者/语言,并加载封面图字节。"""
        opf_path = self._find_file(html_dir, ".opf")
        result.title = Path(file_path).stem  # 兜底
        if not opf_path:
            return
        try:
            tree = ET.parse(opf_path)
            root = tree.getroot()
        except Exception:
            return

        dc = "{http://purl.org/dc/elements/1.1/}"
        title_el = root.find(f".//{dc}title")
        if title_el is not None and (title_el.text or "").strip():
            result.title = title_el.text.strip()
        result.authors = [
            (el.text or "").strip()
            for el in root.iter(f"{dc}creator")
            if (el.text or "").strip()
        ]
        lang_el = root.find(f".//{dc}language")
        if lang_el is not None and (lang_el.text or "").strip():
            result.language = lang_el.text.strip()

        # 封面:opf 里 <meta name="cover" content="ID"> → manifest item href
        cover_bytes = self._extract_cover(root, opf_path, html_dir)
        if cover_bytes:
            result.cover_bytes = cover_bytes

    @staticmethod
    def _extract_cover(root, opf_path: str, html_dir: str) -> bytes | None:
        opf_ns = "{http://www.idpf.org/2007/opf}"
        cover_id = None
        for meta in root.iter(f"{opf_ns}meta"):
            if meta.get("name") == "cover":
                cover_id = meta.get("content")
                break
        href = None
        for item in root.iter(f"{opf_ns}item"):
            item_id = item.get("id")
            media = (item.get("media-type") or "").lower()
            if cover_id and item_id == cover_id:
                href = item.get("href")
                break
            # 回退:manifest 里名字含 cover 的图片
            if href is None and "image" in media and "cover" in (item.get("href") or "").lower():
                href = item.get("href")
        if not href:
            return None
        # href 相对 opf 所在目录
        cover_path = os.path.normpath(os.path.join(os.path.dirname(opf_path), href))
        if not os.path.isfile(cover_path):
            cover_path = os.path.normpath(os.path.join(html_dir, href))
        try:
            with open(cover_path, "rb") as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def _find_file(directory: str, suffix: str) -> str | None:
        if not directory or not os.path.isdir(directory):
            return None
        for name in os.listdir(directory):
            if name.lower().endswith(suffix):
                return os.path.join(directory, name)
        return None
