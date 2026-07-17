# ── 单阶段:后端运行时 + 预先构建的前端产物
FROM python:3.11-slim

# 换 Debian apt 源为清华镜像(bookworm 使用 deb822 格式的 debian.sources)
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list 2>/dev/null || true

# PyMuPDF / Pillow 运行所需系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip 换清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先装依赖以利用构建缓存
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY backend/ .

# 前端构建产物:由 FastAPI 直接托管(单容器,无需 nginx)
COPY frontend/dist /app/frontend_dist

RUN mkdir -p /app/storage/covers /data/db

EXPOSE 8000

# 启动:执行迁移 → 启动应用(SQLite 单文件,无需等待外部 DB)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
