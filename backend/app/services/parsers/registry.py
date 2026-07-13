"""解析器注册表:按扩展名分发到对应解析器。

新增格式(mobi/漫画压缩包)只需实现 BaseParser 子类并在此注册。
"""
from __future__ import annotations

from app.models.book import BookFormat
from app.services.parsers.base import BaseParser
from app.services.parsers.epub import EpubParser
from app.services.parsers.pdf import PdfParser
from app.services.parsers.txt import TxtParser

# 扩展名(小写,不含点)→ 解析器实例
_PARSERS: list[BaseParser] = [TxtParser(), EpubParser(), PdfParser()]

_BY_EXT: dict[str, BaseParser] = {}
for _p in _PARSERS:
    for _ext in _p.extensions:
        _BY_EXT[_ext] = _p

# 扩展名 → 数据库枚举 BookFormat
_EXT_TO_FORMAT: dict[str, BookFormat] = {
    "txt": BookFormat.txt,
    "text": BookFormat.txt,
    "epub": BookFormat.epub,
    "pdf": BookFormat.pdf,
}

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(_BY_EXT.keys())


def get_parser(ext: str) -> BaseParser | None:
    return _BY_EXT.get(ext.lower().lstrip("."))


def get_format(ext: str) -> BookFormat | None:
    return _EXT_TO_FORMAT.get(ext.lower().lstrip("."))
