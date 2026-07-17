"""v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    books,
    reading_settings,
    scrape,
    settings,
    shelves,
    sources,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(settings.router)
api_router.include_router(sources.router)
api_router.include_router(books.router)
api_router.include_router(shelves.router)
api_router.include_router(reading_settings.router)
api_router.include_router(scrape.router)
