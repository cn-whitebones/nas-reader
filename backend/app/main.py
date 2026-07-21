"""FastAPI 应用入口。"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse, Response

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

    JWT_SECRET 弱值直接拒绝启动(伪造令牌的安全边界,修改无副作用)。
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

# 开发环境放开 CORS;单容器生产为同源,无需 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文本资源(html/js/css/json)gzip 压缩,替代原 nginx 的压缩能力
app.add_middleware(GZipMiddleware, minimum_size=1024)


# 全局异常处理:统一错误响应格式,记录未处理异常
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的异常。

    - HTTPException:保留状态码和 detail
    - 其他异常:记录日志,返回 500 错误,不泄露内部细节给客户端
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    # 未处理异常:记录日志,返回通用错误信息
    logger.exception("未处理的异常: %s", str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok"}


# ── 前端静态托管(单容器)────────────────────────────────────────────────
# 前端构建产物存在时,由本进程直接托管,去掉独立的 nginx 容器。
# 本地纯后端开发(dist 不存在)时自动跳过,不影响 uvicorn 启动。
_DIST = settings.frontend_dist
# 每次请求都需拉取最新的文件(PWA 更新依赖):不缓存
_NO_CACHE = {"Cache-Control": "no-cache, no-store, must-revalidate"}
# 带内容 hash 的资源:文件名变化即失效,可长期强缓存
_IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}


def _index_response() -> FileResponse:
    return FileResponse(os.path.join(_DIST, "index.html"), headers=_NO_CACHE)


if os.path.isdir(_DIST):

    @app.get("/", include_in_schema=False)
    async def spa_root():
        return _index_response()

    @app.get("/assets/{asset_path:path}", include_in_schema=False)
    async def assets(asset_path: str):
        """带 hash 的静态资源:长期强缓存。"""
        candidate = os.path.normpath(os.path.join(_DIST, "assets", asset_path))
        assets_root = os.path.join(_DIST, "assets")
        if candidate.startswith(assets_root) and os.path.isfile(candidate):
            return FileResponse(candidate, headers=_IMMUTABLE)
        return Response(status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """SPA 路由回退:非 API 路径一律返回对应静态文件或 index.html。

        PWA 关键文件(sw.js / manifest)显式 no-cache,保证更新及时生效。
        """
        # 未命中的 API 路径应返回 404,而非被吞成 HTML
        if full_path.startswith("api/"):
            return Response(status_code=404)
        candidate = os.path.normpath(os.path.join(_DIST, full_path))
        # 防目录穿越:必须仍在 dist 内
        if candidate.startswith(_DIST) and os.path.isfile(candidate):
            if full_path in ("sw.js", "manifest.webmanifest", "index.html"):
                return FileResponse(candidate, headers=_NO_CACHE)
            return FileResponse(candidate)
        # 未命中实体文件 → 交给前端路由处理
        return _index_response()
else:
    logger.info("未找到前端构建产物目录 %s,跳过静态托管(纯后端模式)", _DIST)
