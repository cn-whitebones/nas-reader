"""电子书解析器抽象层。

每种格式实现 BaseParser,提供:章节提取、封面提取、章节内容读取。
新增格式(mobi/漫画)时新增一个子类并在 registry 注册即可。
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def clean_html_body(html: str) -> str:
    """从完整 HTML/XHTML 文档中提取 <body> 内的内容,去掉 XML 声明、DOCTYPE、head。

    避免完整文档结构(特别是带 namespace 的 XHTML)导致前端 v-html 渲染异常。
    """
    # 去掉 XML 声明
    html = re.sub(r'^<\?xml[^>]*\?>', '', html, count=1, flags=re.IGNORECASE)
    # 去掉 DOCTYPE
    html = re.sub(r'^<!DOCTYPE[^>]*>', '', html, count=1, flags=re.IGNORECASE)
    # 提取 body 内容
    body_match = re.search(r'<body[^>]*>(.*)</body>', html, flags=re.DOTALL | re.IGNORECASE)
    if body_match:
        html = body_match.group(1)
    # 去掉外层 html 标签(如果没有 body 但有 html 的话)
    else:
        html = re.sub(r'^<html[^>]*>', '', html, count=1, flags=re.IGNORECASE)
        html = re.sub(r'</html>$', '', html, count=1, flags=re.IGNORECASE)
        html = re.sub(r'^<head[^>]*>.*?</head>', '', html, count=1, flags=re.DOTALL | re.IGNORECASE)
    return html.strip()


@dataclass
class ParsedChapter:
    idx: int
    title: str
    location: str  # 格式相关定位:pdf=页码, epub=href, txt=字符偏移


@dataclass
class ParsedBook:
    chapters: list[ParsedChapter] = field(default_factory=list)
    cover_bytes: bytes | None = None  # 原始封面图字节(由扫描器落盘)
    # 从文件内嵌信息提取的元数据(可为空,后续可被刮削覆盖)
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    language: str | None = None
    # 字数:txt/epub/mobi 统计;pdf/漫画无法可靠统计,保持 None
    word_count: int | None = None


def count_words(text: str) -> int:
    """统计正文字数:中文按字符计,英文按单词计。

    去除空白后,CJK 字符逐字计数,连续的非 CJK(英文/数字)串按空白切词计数。
    这样中英文混排都能得到贴近直觉的「字数」。
    """
    if not text:
        return 0
    cjk = 0
    latin_runs = 0
    in_run = False
    for ch in text:
        if ch.isspace():
            in_run = False
            continue
        # CJK 统一表意文字及扩展、假名等主要区段
        if "㐀" <= ch <= "鿿" or "豈" <= ch <= "﫿" or "぀" <= ch <= "ヿ":
            cjk += 1
            in_run = False
        else:
            if not in_run:
                latin_runs += 1
                in_run = True
    return cjk + latin_runs


class BaseParser(ABC):
    """解析器基类。所有方法应对损坏文件健壮,失败时返回空而非抛出。"""

    #: 该解析器支持的扩展名(小写,不含点)
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, file_path: str) -> ParsedBook:
        """解析文件,提取章节、封面、内嵌元数据。"""
        raise NotImplementedError

    @abstractmethod
    def read_chapter(
        self, file_path: str, chapter: ParsedChapter, next_location: str | None = None
    ) -> str:
        """读取指定章节的正文,返回 HTML(供前端重排)。

        next_location 为下一章的定位(用于确定本章结束边界),末章为 None。
        pdf 由前端 pdf.js 直接渲染原文件,不走此方法。
        """
        raise NotImplementedError
