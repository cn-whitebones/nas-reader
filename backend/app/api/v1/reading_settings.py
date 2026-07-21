"""阅读设置路由:每用户一份阅读界面偏好。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.reading import ReadingSettings
from app.models.user import User
from app.schemas.book import ReadingSettingsOut, ReadingSettingsUpdate

router = APIRouter(tags=["reading-settings"])


async def _get_or_create(db: AsyncSession, user_id) -> ReadingSettings:
    rs = await db.get(ReadingSettings, user_id)
    if rs is None:
        rs = ReadingSettings(user_id=user_id)
        db.add(rs)
        await db.commit()
        await db.refresh(rs)
    return rs


@router.get("/reading-settings", response_model=ReadingSettingsOut)
async def get_settings(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _get_or_create(db, user.id)


@router.patch("/reading-settings", response_model=ReadingSettingsOut)
async def update_settings(
    payload: ReadingSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rs = await _get_or_create(db, user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rs, key, value)
    await db.commit()
    await db.refresh(rs)
    return rs
