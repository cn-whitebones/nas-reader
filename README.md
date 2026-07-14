# NAS Reader — 电子书管理与阅读应用

面向 NAS 场景的自托管电子书管理与在线阅读应用。通过 docker-compose 一键部署，把本地/NAS 上的书目录映射进容器即可管理和阅读。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.11 + FastAPI + SQLAlchemy(async) + Alembic |
| 数据库 | SQLite(单文件,零运维) |
| 前端 | Vue 3 + Vite + TypeScript + Pinia + Element Plus |
| 阅读器 | txt/epub/mobi 前端重排渲染；pdf 用 pdf.js 原生渲染；漫画自动旋转 |
| 后台任务 | 进程内 APScheduler(扫描/刮削) |
| 部署 | docker-compose 单容器(FastAPI 同时托管 API 与前端静态资源) |

## 功能

- 📁 **文件源管理**:映射目录为文件源，手动 + 自动扫描，扫描进度实时可见
- 📚 **图书库**:按文件夹层级浏览，支持多种格式
- ⭐ **书架**:每用户单一默认书架，一键收藏/取消
- 🔍 **搜索**:按文件名 + 元数据(标题/作者/标签/描述)模糊匹配
- 🏷️ **刮削**:多源降级(豆瓣网页抓取 → Google Books → Open Library → 手动)
- 👥 **多用户**:管理员创建用户并授权，支持默认文件夹权限；支持修改密码
- 📖 **阅读**:
  - 文本类(txt/epub/mobi):字体/字号/行距/边距/主题设置
  - PDF:原生渲染
  - 漫画(zip/cbz/rar/cbr):横图自动旋转 90° 放大显示，点击区自适应
  - 跨章节翻页动画，切后台/关闭页面进度兜底保存
- 📱 **PC/移动端自适应**:H5，iOS PWA 全屏无白边，管理页移动端卡片布局

当前支持 **txt / epub / pdf / mobi / zip / cbz / rar / cbr**，漫画压缩包支持自动识别横图旋转。

## 快速开始

### 方式一:直接使用已发布镜像(推荐,免构建)

镜像已发布到 Docker Hub([`whitebones/nas-reader`](https://hub.docker.com/r/whitebones/nas-reader)),支持 `linux/amd64` 与 `linux/arm64`。

```bash
# 1. 下载编排文件与环境变量模板
curl -O https://gitea.whitebones.cn:33333/wangwanxiong/nas-reader/raw/branch/main/docker-compose.hub.yml
curl -o .env https://gitea.whitebones.cn:33333/wangwanxiong/nas-reader/raw/branch/main/.env.example

# 2. 编辑 .env,至少修改 JWT_SECRET(可用 openssl rand -hex 32 生成)
# 3. 编辑 docker-compose.hub.yml,把你的书目录映射进 volumes
#    例如:  - /volume1/books:/data/book1:ro

# 4. 拉取并启动
docker compose -f docker-compose.hub.yml up -d

# 5. 访问 http://<host>:8080,首次进入引导页创建管理员
```

后续升级到新版本:`docker compose -f docker-compose.hub.yml pull && docker compose -f docker-compose.hub.yml up -d`

### 方式二:从源码本地构建

```bash
# 1. 准备环境变量
cp .env.example .env
# 编辑 .env，至少修改 JWT_SECRET
# (生产环境弱密钥会拒绝启动;可用 openssl rand -hex 32 生成)

# 2. 映射你的书目录：编辑 docker-compose.yml 中 volumes
#    例如:  - /volume1/books:/data/book1:ro

# 3. 启动(单容器)
docker compose up -d --build

# 4. 访问 http://<host>:8080
#    首次访问会进入引导页，创建管理员账号
```

启动后：
1. 用引导页创建的管理员登录
2. **管理 → 文件源**：添加映射进来的目录(容器内路径，如 `/data/book1`)为文件源，触发扫描
3. **管理 → 用户**：创建用户并授权可访问的文件源
4. 回到**书库**浏览、阅读

> **数据与备份**:所有数据存于单个 SQLite 文件(`dbdata` 卷内 `/data/db/nasreader.db`),封面缩略图存于 `covers` 卷。备份只需复制这两个卷(或 `docker cp` 出 `.db` 文件)。无独立数据库容器,零运维。

## 目录结构

```
nas-reader/
├── docker-compose.yml
├── .env.example
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── core/     # 配置、安全、依赖注入
│   │   ├── db/       # 数据库会话
│   │   ├── models/   # ORM 模型
│   │   ├── schemas/  # Pydantic 模型
│   │   ├── api/v1/   # 路由
│   │   └── services/ # 扫描、解析器、刮削、后台任务
│   └── alembic/      # 数据库迁移
└── frontend/         # Vue 3 前端
    └── src/
        ├── api/      # 接口封装
        ├── stores/   # Pinia 状态
        ├── router/
        ├── views/    # 页面
        └── reader/   # 阅读器核心
```

## 开发模式

```bash
# 后端
cd backend
pip install -e ".[dev]"
# 默认用 SQLite,可通过 DATABASE_URL 覆盖;不设则落到 /data/db(需可写)
# 本地开发建议: export DATABASE_URL="sqlite+aiosqlite:///./nasreader.db"
alembic upgrade head
uvicorn app.main:app --reload

# 前端(另开终端)
cd frontend
npm install
npm run dev   # 默认 http://localhost:5173，已代理 /api 到 :8000
```

## 数据模型

`users` `permissions` `sources` `scan_tasks` `books` `book_metadata` `chapters`
`shelves` `shelf_books` `reading_progress` `reading_settings`

- 图书以 `file_hash`(内容首段哈希 + 大小)作稳定标识，文件移动/改名不丢阅读进度
- 磁盘文件删除后图书标记为 `missing`，保留记录与进度
- 阅读进度存 `location`(格式相关定位)+ `percent`(统一百分比)

## 开发进度 v1.1

- [x] 后端骨架(FastAPI + DB + 鉴权 + 用户/权限/引导)
- [x] 前端骨架(路由 + 鉴权 + 引导/登录/布局)
- [x] Docker 编排，生产环境弱密钥启动校验
- [x] 文件扫描与格式解析器(txt/epub/pdf，章节+封面提取)
- [x] MOBI 格式支持(KF8 epub 内部 + MOBI7 html)
- [x] 漫画压缩包支持(zip/cbz/rar/cbr)，横图自动旋转适配
- [x] 图书库 / 搜索 / 书架 / 进度 API，进度切后台兜底保存
- [x] 元数据刮削(豆瓣网页抓取 → Google Books → Open Library → 手动)
- [x] 阅读器(txt/epub 重排 + pdf.js；字体/字号/行距/边距/主题)
- [x] 跨章节翻页方向动画，顶栏内容避让
- [x] PC/移动端自适应(登录页/书架/详情/管理页卡片布局)
- [x] iOS PWA 全屏底部白边修复
- [x] 书库列表/网格双视图切换(localStorage 记忆)

## v1.2 架构精简

- [x] 数据库 PostgreSQL → SQLite(单文件,零运维,备份即复制)
- [x] 前后端合并为单容器(FastAPI 托管前端静态资源 + SPA 回退 + PWA 缓存头)
- [x] 部署从三容器(frontend/backend/postgres)精简为一个容器
