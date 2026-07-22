# ── 单阶段:后端运行时 + 预先构建的前端产物
FROM python:3.11-slim

# 换 Debian apt 源为清华镜像(bookworm 使用 deb822 格式的 debian.sources)
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

# PyMuPDF / Pillow 运行所需系统库 + curl (用于健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 换清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 创建非 root 用户
RUN groupadd -r nasreader && useradd -r -g nasreader nasreader

# 先装依赖以利用构建缓存
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY backend/ .

# 前端构建产物:由 FastAPI 直接托管(单容器,无需 nginx)
COPY frontend/dist /app/frontend_dist

# 创建数据目录并授权给非 root 用户
RUN mkdir -p /app/storage/covers /data/db \
    && chown -R nasreader:nasreader /app /data

# 切换到非 root 用户
USER nasreader

EXPOSE 8000

# 健康检查:NAS 容器管理可以显示状态
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动:执行迁移 → exec 替换 shell 替换自身为 uvicorn (正确传递信号)
# exec 让 uvicorn 成为 PID 1，docker stop 能立即停止
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
