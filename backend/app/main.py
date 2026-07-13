"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动:初始化后台调度器,并为开启自动扫描的文件源注册周期任务
    from app.services.tasks import register_auto_scans, scheduler

    scheduler.start()
    try:
        await register_auto_scans()
    except Exception:
        # DB 尚未就绪等情况不应阻断启动
        pass
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, openapi_url=f"{settings.api_prefix}/openapi.json", lifespan=lifespan)

# 开发环境放开 CORS;生产由 nginx 同源反代,可收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}
