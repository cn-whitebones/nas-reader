"""排序键工具:把中文书名/作者转为可稳定排序的拼音键。

SQLite 无内置拼音排序,故在入库时预生成排序键存列,排序分页时直接按该列排。
规则:逐字符处理——中文取全拼(小写),其余字符原样转小写保留;这样
「三体」→「santi」、「Python」→「python」,中英文混排也能得到一致的字典序。
"""
from __future__ import annotations

from pypinyin import Style, lazy_pinyin


def to_sort_key(text: str | None) -> str:
    """生成排序键:中文转全拼小写,其他字符保留并小写。空值返回空串。"""
    if not text:
        return ""
    # lazy_pinyin 对中文返回拼音,对非中文字符原样返回(不拆分)
    parts = lazy_pinyin(text.strip(), style=Style.NORMAL, errors="default")
    return "".join(parts).lower()


def authors_sort_key(authors: list[str] | None) -> str:
    """用首个作者生成排序键。"""
    if not authors:
        return ""
    return to_sort_key(authors[0])
