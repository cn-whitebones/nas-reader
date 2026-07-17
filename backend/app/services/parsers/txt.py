"""TXT 格式解析器:按章节标题识别章节,按字符偏移定位。

中文 txt 章节标题写法极不统一,实测需覆盖三类:
  1. 强模式  「第X章/回/节/卷/篇/部/集/折」          —— 最规范
  2. 弱模式  「X + 分隔(全角空格/tab/顿号/多空格) + 标题」或纯数字行 X
             例:金庸多数作品用「一　　青衫磊落险峰行」甚至只有「一」
  3. 特殊无序号  楔子/序章/序言/引子/尾声/后记/番外/附录 等

单纯正则匹配会把「正文目录」「散落的数字行」也当成章节(如鹿鼎记正文里
孤立的「六」「两」)。因此在正则之上再用「序号单调递增 + 同序号取最后一次
出现」两条约束过滤:目录里的重复序号被正文覆盖,正文里不递增的数字被丢弃。
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.services.parsers.base import BaseParser, ParsedBook, ParsedChapter

_NUM = "[0-9零〇一二三四五六七八九十百千两]"
# 强模式:第X章/回/…
_STRONG_RE = re.compile(rf"^\s*第\s*({_NUM}{{1,7}})\s*[章节回卷篇部集折].{{0,30}}$")
_EN_RE = re.compile(r"^\s*Chapter\s+(\d+)\b.{0,30}$", re.IGNORECASE)
# 弱模式:数字 + 分隔符(全角空格/tab/顿号/点/≥2半角空格) + 标题
_WEAK_TITLE_RE = re.compile(rf"^\s*({_NUM}{{1,7}})\s*(?:[　\t、．.]|[ ]{{2,}})\s*\S.{{0,28}}$")
# 弱模式:纯数字行(仅一个序号,无标题)
_WEAK_PURE_RE = re.compile(rf"^\s*({_NUM}{{1,7}})\s*$")
# 特殊无序号章节
_SPECIAL_RE = re.compile(r"^\s*(?:楔子|序章|序言|序幕|前言|引子|尾声|终章|后记|番外篇?|附录).{0,20}$")

_MAX_TITLE_LEN = 60
_MIN_SEQ_CHAPTERS = 3  # 至少识别到这么多带序号的章节才认可,否则视为无章节
_FALLBACK_CHUNK = 5000  # 无章节时按此字符数分块

# 编码尝试顺序:utf-8(含BOM)→ gb18030(GBK/GB2312超集,覆盖简体中文旧书)→ big5(繁体)
_ENCODINGS = ("utf-8-sig", "gb18030", "big5")

_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def _to_int(s: str) -> int:
    """把「阿拉伯/中文」数字串转成整数,用于章节序号比较。解析失败返回 -1。"""
    s = s.strip()
    if s.isdigit():
        return int(s)
    total = cur = 0
    for ch in s:
        if ch in _CN_DIGIT:
            cur = _CN_DIGIT[ch]
        elif ch in _CN_UNIT:
            total += (cur or 1) * _CN_UNIT[ch]
            cur = 0
        else:
            return -1
    return total + cur


def _clean_title(s: str) -> str:
    """压缩标题内连续空白(含全角空格/tab)为单个半角空格,便于展示。"""
    return re.sub(r"[\s　]+", " ", s).strip()


@lru_cache(maxsize=8)
def _read_text(file_path: str) -> str:
    """读取整篇文本并自动探测编码(带小缓存,避免同一文件反复读盘)。

    中文 txt 常见 GBK/GB2312 编码,不能写死 utf-8 否则整篇乱码。
    依次严格尝试各编码,首个成功者胜;全失败时用 utf-8 容错模式兜底。
    """
    try:
        raw = Path(file_path).read_bytes()
    except Exception:
        return ""
    for enc in _ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    # 全部失败:utf-8 容错,至少不崩
    return raw.decode("utf-8", errors="replace")


class TxtParser(BaseParser):
    extensions = ("txt", "text")

    def parse(self, file_path: str) -> ParsedBook:
        text = _read_text(file_path)
        chapters = self._detect_chapters(text)
        if not chapters:
            # 无标准章节标题 → 按固定字符数分块
            for i in range(0, max(len(text), 1), _FALLBACK_CHUNK):
                chunk_head = text[i : i + 40].strip().splitlines()
                title = (chunk_head[0][:40] if chunk_head else "") or f"第 {i // _FALLBACK_CHUNK + 1} 节"
                chapters.append(ParsedChapter(idx=len(chapters), title=title, location=str(i)))
        return ParsedBook(chapters=chapters)

    @staticmethod
    def _detect_chapters(text: str) -> list[ParsedChapter]:
        """扫描全文,识别带序号/特殊章节标题。返回按偏移排序的章节列表。

        strong/weak/special 三类候选各自收集;若强模式或弱模式达到最小数量,
        对其做「同序号取最后一次 + 序号单调递增」过滤,再并入无序号的特殊章节。
        """
        # 候选: (offset, seq, kind, title);special 的 seq 为 None
        strong: list[tuple[int, int, str]] = []
        weak: list[tuple[int, int, str]] = []
        special: list[tuple[int, str]] = []

        offset = 0
        for line in text.splitlines(keepends=True):
            off = offset
            offset += len(line)
            s = line.strip()
            if not s or len(s) > _MAX_TITLE_LEN:
                continue
            m = _STRONG_RE.match(s) or _EN_RE.match(s)
            if m:
                strong.append((off, _to_int(m.group(1)), s))
                continue
            if _SPECIAL_RE.match(s):
                special.append((off, s))
                continue
            m = _WEAK_TITLE_RE.match(s) or _WEAK_PURE_RE.match(s)
            if m:
                weak.append((off, _to_int(m.group(1)), s))

        if len(strong) >= _MIN_SEQ_CHAPTERS:
            seq_cands = strong
        elif len(weak) >= _MIN_SEQ_CHAPTERS:
            seq_cands = weak
        else:
            seq_cands = []

        # 同一序号保留「最后一次」出现:目录中的重复标题会被正文覆盖
        by_seq: dict[int, tuple[int, int, str]] = {}
        for cand in seq_cands:
            if cand[1] >= 0:
                by_seq[cand[1]] = cand
        # 序号单调递增:过滤掉正文里散落的、不构成递增序列的数字行
        kept: list[tuple[int, str]] = []
        last = -1
        for off, seq, title in sorted(by_seq.values(), key=lambda c: c[0]):
            if seq > last:
                kept.append((off, title))
                last = seq

        merged = kept + [(off, title) for off, title in special]
        merged.sort(key=lambda c: c[0])
        return [
            ParsedChapter(idx=i, title=_clean_title(title)[:120], location=str(off))
            for i, (off, title) in enumerate(merged)
        ]

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
