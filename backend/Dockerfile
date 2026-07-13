FROM python:3.11-slim

# PyMuPDF / Pillow 运行所需系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖以利用构建缓存
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

COPY . .

RUN mkdir -p /app/storage/covers

EXPOSE 8000

# 启动脚本:等待 DB → 迁移 → 启动
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
