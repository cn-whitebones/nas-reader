"""系统设置路由:默认文件夹权限模板、刮削配置、刮削源管理(仅管理员)。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models.user import Permission
from app.schemas.auth import PermissionItem, PermissionUpdate
from app.services.settings_store import (
    KEY_DOUBAN_COOKIE,
    PROVIDER_LABELS,
    get_provider_config,
    get_setting,
    set_provider_config,
    set_setting,
)

router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_admin)])


class ScrapeSettingsOut(BaseModel):
    """刮削设置。出于安全考虑不回传完整 Cookie,仅返回是否已配置与长度。"""

    douban_cookie_set: bool
    douban_cookie_length: int


class ScrapeSettingsUpdate(BaseModel):
    douban_cookie: str


class ProviderItem(BaseModel):
    provider: str
    enabled: bool
    label: str | None = None


class ProviderConfigUpdate(BaseModel):
    providers: list[ProviderItem]


def _with_labels(config: list[dict]) -> list[ProviderItem]:
    label_by_value = {k.value: v for k, v in PROVIDER_LABELS.items()}
    return [
        ProviderItem(
            provider=item["provider"],
            enabled=item["enabled"],
            label=label_by_value.get(item["provider"], item["provider"]),
        )
        for item in config
    ]


@router.get("/scrape", response_model=ScrapeSettingsOut)
async def get_scrape_settings(db: AsyncSession = Depends(get_db)):
    cookie = await get_setting(db, KEY_DOUBAN_COOKIE, "")
    return ScrapeSettingsOut(douban_cookie_set=bool(cookie), douban_cookie_length=len(cookie))


@router.put("/scrape", response_model=ScrapeSettingsOut)
async def update_scrape_settings(payload: ScrapeSettingsUpdate, db: AsyncSession = Depends(get_db)):
    """更新豆瓣 Cookie。传空字符串即清除(回退到环境变量)。"""
    await set_setting(db, KEY_DOUBAN_COOKIE, payload.douban_cookie.strip())
    cookie = await get_setting(db, KEY_DOUBAN_COOKIE, "")
    return ScrapeSettingsOut(douban_cookie_set=bool(cookie), douban_cookie_length=len(cookie))


@router.get("/scrape/providers", response_model=list[ProviderItem])
async def get_scrape_providers(db: AsyncSession = Depends(get_db)):
    """刮削源顺序与启用状态(顺序即自动模式的降级顺序)。"""
    return _with_labels(await get_provider_config(db))


@router.put("/scrape/providers", response_model=list[ProviderItem])
async def set_scrape_providers(payload: ProviderConfigUpdate, db: AsyncSession = Depends(get_db)):
    config = [{"provider": p.provider, "enabled": p.enabled} for p in payload.providers]
    saved = await set_provider_config(db, config)
    return _with_labels(saved)


@router.get("/default-permissions", response_model=list[PermissionItem])
async def get_default_permissions(db: AsyncSession = Depends(get_db)):
    """默认权限模板:user_id 为 NULL 的权限行,新建用户时据此初始化。"""
    result = await db.execute(select(Permission).where(Permission.user_id.is_(None)))
    return list(result.scalars().all())


@router.put("/default-permissions", response_model=list[PermissionItem])
async def set_default_permissions(payload: PermissionUpdate, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(Permission).where(Permission.user_id.is_(None)))
    for item in payload.permissions:
        db.add(
            Permission(
                user_id=None,
                source_id=item.source_id,
                sub_path=item.sub_path,
                can_read=item.can_read,
            )
        )
    await db.commit()
    result = await db.execute(select(Permission).where(Permission.user_id.is_(None)))
    return list(result.scalars().all())
