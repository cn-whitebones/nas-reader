"""文件系统辅助:稳定哈希、安全路径校验。"""
from __future__ import annotations

import os
from pathlib import Path

import xxhash

from app.core.config import settings


def compute_file_hash(file_path: str, size: int) -> str:
    """以文件首段内容 + 文件大小生成稳定标识。

    只读首段(默认 1MB)以兼顾大文件性能;拼上 size 降低碰撞概率。
    文件被移动/改名后该值不变,可用于重新关联进度。
    """
    h = xxhash.xxh64()
    try:
        with open(file_path, "rb") as f:
            h.update(f.read(settings.scan_hash_read_bytes))
    except OSError:
        return ""
    h.update(str(size).encode())
    return h.hexdigest()


def is_within(base: str, target: str) -> bool:
    """target 是否位于 base 目录内(防目录穿越)。"""
    try:
        base_r = Path(base).resolve()
        target_r = Path(target).resolve()
        return base_r == target_r or base_r in target_r.parents
    except OSError:
        return False


def safe_join(root: str, rel_path: str) -> str | None:
    """把相对路径安全拼接到 root 下,越界返回 None。"""
    joined = os.path.normpath(os.path.join(root, rel_path))
    if not is_within(root, joined):
        return None
    return joined
