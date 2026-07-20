"""应用设置服务:运行时可编辑的 key-value 配置,DB 优先、环境变量兜底。

目前用于豆瓣 Cookie、刮削源顺序/启用等需要管理员在后台修改的刮削配置。
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as env_settings
from app.models.book import MetadataProviderName
from app.models.setting import AppSetting

# 设置项 key 常量
KEY_DOUBAN_COOKIE = "douban_cookie"
KEY_SCRAPE_PROVIDERS = "scrape_providers"

# 刮削源默认顺序与启用状态(豆瓣中文书友好但不稳定,置顶)
_DEFAULT_PROVIDER_ORDER = [
    MetadataProviderName.douban,
    MetadataProviderName.google,
    MetadataProviderName.openlibrary,
]
PROVIDER_LABELS = {
    MetadataProviderName.douban: "豆瓣读书",
    MetadataProviderName.google: "Google Books",
    MetadataProviderName.openlibrary: "Open Library",
}


async def get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    row = await db.get(AppSetting, key)
    return row.value if row and row.value else default


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(AppSetting, key)
    if row is None:
        row = AppSetting(key=key, value=value)
        db.add(row)
    else:
        row.value = value
    await db.commit()


async def get_douban_cookie(db: AsyncSession) -> str:
    """豆瓣 Cookie:DB 设置优先,未设置则回退到环境变量 DOUBAN_COOKIE。"""
    return await get_setting(db, KEY_DOUBAN_COOKIE, env_settings.douban_cookie)


def _default_provider_config() -> list[dict]:
    return [{"provider": p.value, "enabled": True} for p in _DEFAULT_PROVIDER_ORDER]


async def get_provider_config(db: AsyncSession) -> list[dict]:
    """刮削源配置:[{provider, enabled}],按存储顺序即为刮削降级顺序。

    与默认列表合并,保证:新增的内置源不会因旧配置而丢失,非法项被忽略。
    """
    raw = await get_setting(db, KEY_SCRAPE_PROVIDERS, "")
    stored: list[dict] = []
    if raw:
        try:
            stored = json.loads(raw)
        except (ValueError, TypeError):
            stored = []

    valid_names = {p.value for p in _DEFAULT_PROVIDER_ORDER}
    result: list[dict] = []
    seen: set[str] = set()
    for item in stored:
        if not isinstance(item, dict):
            continue
        name = item.get("provider")
        if name in valid_names and name not in seen:
            result.append({"provider": name, "enabled": bool(item.get("enabled", True))})
            seen.add(name)
    # 补齐配置里缺失的内置源(默认启用,追加到末尾)
    for p in _DEFAULT_PROVIDER_ORDER:
        if p.value not in seen:
            result.append({"provider": p.value, "enabled": True})
    return result


async def set_provider_config(db: AsyncSession, config: list[dict]) -> list[dict]:
    """保存刮削源配置。仅接受合法内置源,保存后返回规范化结果。"""
    valid_names = {p.value for p in _DEFAULT_PROVIDER_ORDER}
    normalized: list[dict] = []
    seen: set[str] = set()
    for item in config:
        name = item.get("provider")
        if name in valid_names and name not in seen:
            normalized.append({"provider": name, "enabled": bool(item.get("enabled", True))})
            seen.add(name)
    for p in _DEFAULT_PROVIDER_ORDER:
        if p.value not in seen:
            normalized.append({"provider": p.value, "enabled": True})
    await set_setting(db, KEY_SCRAPE_PROVIDERS, json.dumps(normalized))
    return normalized

