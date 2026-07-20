"""应用设置服务:运行时可编辑的 key-value 配置,DB 优先、环境变量兜底。

目前用于豆瓣 Cookie 等需要管理员在后台修改的刮削配置。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as env_settings
from app.models.setting import AppSetting

# 设置项 key 常量
KEY_DOUBAN_COOKIE = "douban_cookie"


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
