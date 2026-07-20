# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

NAS Reader — 面向 NAS 场景的自托管电子书管理与在线阅读应用。
单容器部署，支持 txt / epub / pdf / mobi / 漫画(zip/cbz/rar/cbr) 等格式。

## 技术架构

```
┌───────────────────────────────────────────────────────────┐
│                    FastAPI (单容器部署)                     │
│  ┌────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  Vue 3 SPA  │  │   Python Backend  │  │   SQLite DB    │  │
│  │  (托管于    │  │   (API + 逻辑)    │  │   (单文件)     │  │
│  │   /static)  │  │   Auth / Books    │  │  books/chapters│  │
│  │             │  │   Scan / Parser   │  │  progress etc  │  │
│  └────────────┘  └─────────────────┘  └───────────────┘  │
│       │                        │                             │
│       │            ┌───────────┴───────────┐               │
│       │            │   APScheduler          │               │
│       │            │   (后台扫描任务)        │               │
│       │            └───────────────────────┘               │
└───────┼──────────────────────────────────────────────────────┘
        │
   挂载书籍目录(NAS)
```

## 项目结构

```
nas-reader/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/         # API 路由 (books.py, shelves.py, etc.)
│   │   ├── models/         # SQLAlchemy ORM 模型
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   ├── services/       # 业务逻辑:扫描/解析/刮削
│   │   ├── core/           # 配置/安全/数据库会话
│   │   └── main.py         # 应用入口
│   ├── alembic/            # 数据库迁移
│   └── Dockerfile          # 单容器镜像
├── frontend/               # Vue 3 + TypeScript + Vite
│   ├── src/
│   │   ├── views/          # 页面组件 (Reader, BookDetail, Library, etc.)
│   │   ├── api/            # API 客户端封装
│   │   ├── stores/         # Pinia 状态管理 (auth, reader)
│   │   └── router/         # 路由配置
│   └── dist/               # 构建产物(由后端托管)
├── docker-compose.yml      # 本地开发编排
└── docker-compose.hub.yml  # 生产环境(使用 Docker Hub 镜像)
```

## 常用命令

### 前端

```bash
cd frontend/

# 安装依赖
npm install

# 开发模式 (端口 5173)
npm run dev

# 构建生产版本
npm run build

# 类型检查
npx vue-tsc --noEmit
```

### 后端

```bash
cd backend/

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"

# 数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 代码检查
ruff check .
ruff format .

# 运行测试 (暂无测试)
# pytest
```

### Docker

```bash
# 构建并启动本地开发环境
docker compose up -d --build

# 查看日志
docker compose logs -f nas-reader

# 重启
docker compose restart

# 使用预构建镜像 (生产环境)
docker compose -f docker-compose.hub.yml up -d

# 构建多架构镜像并发布到 Docker Hub
docker buildx build --platform linux/amd64,linux/arm64 -t whitebones/nas-reader:latest --push -f backend/Dockerfile .
```

## 重要约定

### 漫画双页阅读功能

1. **后端**: `Book` 模型包含 `double_page` 和 `start_right` 字段，由管理员在书籍详情页设置
2. **前端**: 
   - Reader 组件检测横图后自动切分
   - 普通用户可以本地覆盖设置（localStorage），不影响全局
   - `comicSubPage = 0` = 左半页, `1` = 右半页
   - `start_right = true` = 从右页开始(日漫阅读顺序)

### 代码风格

- **Python**: Ruff 100 行宽，类型注解（Pydantic 模型）
- **TypeScript**: Vue 3 `<script setup>` 语法，使用 Pinia store
- **API 风格**: RESTful，`GET /api/v1/books`，认证使用 JWT Bearer Token

### 数据持久化

- SQLite 数据库文件位于容器内 `/data/db/nasreader.db`
- 封面缩略图位于 `/app/storage/covers`
- 书籍源目录通过 Docker volume 挂载，只读

## 发布流程

新版本发布步骤：

```bash
# 1. 确保代码提交并测试通过
git status

# 2. 本地构建前端
cd frontend && npm run build

# 3. 更新 README.md「开发进度」章节,新增当前版本小节记录本次更新内容
#    (最新版本在上,格式参考已有小节)

# 4. 提交改动并推送
git add -A && git commit -m "..." && git push origin main

# 5. 打 Git tag 并推送
git tag v1.3.0
git push origin v1.3.0

# 6. 构建多架构镜像并推送到 Docker Hub
docker buildx build --platform linux/amd64,linux/arm64 -t whitebones/nas-reader:v1.3.0 -t whitebones/nas-reader:latest --push -f backend/Dockerfile .
```

## 关键文件速查

| 功能 | 文件路径 |
|-----|---------|
| 漫画双页切割逻辑 | `frontend/src/views/Reader.vue` |
| 漫画本地存储 | `reader.vue` + `.comic-pref_{bookId}` localStorage |
| 书籍 API | `backend/app/api/v1/books.py` |
| 权限控制 | `backend/app/core/security.py` |
| 扫描任务 | `backend/app/services/scanner.py` |
| 数据库模型 | `backend/app/models/` |
| 前端 API 封装 | `frontend/src/api/` |
