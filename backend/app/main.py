"""FastAPI 应用入口。"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("nasreader")

# 已知的占位/弱密钥,生产环境使用则拒绝启动
_INSECURE_JWT_SECRETS = {
    "CHANGE_ME_IN_PRODUCTION",
    "please_change_to_a_long_random_secret",
    "change_me",
    "secret",
    "",
}


def _check_production_secrets() -> None:
    """生产模式(debug=False)下校验关键密钥。

    JWT_SECRET 弱值直接拒绝启动(伪造令牌的安全边界,修改无副作用);
    数据库默认密码仅打印警告(强改会与已初始化的数据卷冲突,破坏性大)。
    """
    if settings.debug:
        return
    if settings.jwt_secret.strip() in _INSECURE_JWT_SECRETS or len(settings.jwt_secret) < 16:
        raise RuntimeError(
            "检测到不安全的 JWT_SECRET(默认/弱值),已拒绝启动。\n"
            "请在 .env 中将 JWT_SECRET 改为不少于 16 位的随机字符串,例如:\n"
            "  JWT_SECRET=$(openssl rand -hex 32)\n"
            "(仅本地调试可设置 DEBUG=true 跳过此检查)"
        )
    if "change_this_password" in settings.database_url:
        logger.warning(
            "数据库仍在使用示例密码 change_this_password,建议生产环境修改 "
            "POSTGRES_PASSWORD(注意:需在数据卷首次初始化前设置)。"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动:校验生产密钥,再初始化后台调度器
    _check_production_secrets()

    # 启动:初始化后台调度器,并为开启自动扫描的文件源注册周期任务
    from app.services.tasks import register_auto_scans, scheduler

    scheduler.start()
    try:
        await register_auto_scans()
    except Exception:
        # DB 尚未就绪等情况不应阻断启动
        logger.exception("注册自动扫描任务失败,已忽略以不阻断启动")
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
