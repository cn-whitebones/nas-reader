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
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .

RUN mkdir -p /app/storage/covers

EXPOSE 8000

# 启动脚本:等待 DB → 迁移 → 启动
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
