# NAS Reader 代码开发规范

本文档记录项目代码开发约定，避免重复踩过的坑。

---

## 后端规范

### 1. 代码组织

- **业务逻辑必须放在 `services/` 目录**，API 路由层只负责：
  - 参数校验
  - 请求/响应转换
  - 调用 service 层
  - 返回 HTTP 响应
- **禁止路由间导入私有函数**（如 `from app.api.v1.books import _brief`）
- **共用辅助函数应该放在**：
  - 相关的 service 模块
  - 或 `schemas/` 作为模型类方法（如 `BookBrief.from_model()`）
  - 或 `core/` 通用工具
- 禁止业务逻辑内联在路由函数中

### 2. 错误处理

- **必须增加全局异常处理器**，统一错误响应格式
- **禁止裸 `except Exception:` 吞掉所有异常**，除非有明确理由：
  - 👌 正确：`except SpecificException:`
  - 👌 如果必须捕获所有异常：记录日志后再处理
  - 👎 错误：`except Exception: pass`
- 业务错误使用 `HTTPException` 抛出，状态码符合 HTTP 语义

### 3. 类型注解

- 所有函数必须完整的类型注解（参数 + 返回值）
- 示例：
  ```python
  def get_book(db: AsyncSession, book_id: UUID) -> Book | None:
      ...
  ```

### 4. 常量与硬编码

- 重复出现的字符串/数字必须定义为模块级常量
- 禁止在代码中硬编码魔法数字
- 示例：
  ```python
  # 好
  MAX_COMIC_CACHE_SIZE = 16
  DEBOUNCE_SETTINGS_MS = 600

  # 不好
  def foo():
      ... @lru_cache(maxsize=4)  # 4 硬编码
  ```

### 5. 数据库查询

- 批量查询必须使用 `selectinload` 预加载关联关系，避免 N+1
- 合理使用分页，禁止无限制返回全部结果

### 6. API 路由约定

- **HTTP 方法语义**：
  - `GET`：获取资源
  - `POST`：创建资源
  - `PUT`：全量更新
  - `PATCH`：部分更新
  - `DELETE`：删除
- 统一使用 `Page[T]` 分页模式
- 响应统一使用 Pydantic `response_model`

---

## 前端规范

### 1. 代码组织

- **响应式逻辑抽成 composable**，禁止每个组件重复实现相同逻辑
- 示例：`useViewport()` 处理视口检测

### 2. 状态管理

- 全局共享状态放在 Pinia store
- 跨组件共享状态不要分散在组件内
- 建议 stores：
  - `auth.ts` - 认证状态 ✅ 已有
  - `reader.ts` - 阅读设置 ✅ 已有
  - `books.ts` - 书库筛选/列表状态
  - `shelves.ts` - 书架状态
  - `reading.ts` - 当前阅读会话状态

### 3. 本地存储

- 所有 localStorage 键必须加前缀 `nas-reader:`
- 👌 正确：`nas-reader:access-token`
- 👎 错误：`access_token`（无前缀，容易冲突）

### 4. 重复代码

- Blob URL 必须统一管理，使用 LRU 缓存限制数量
- 每个组件自己 `URL.createObjectURL()` 后必须 `revoke()`，容易泄漏
- 统一管理后避免泄漏

### 5. 错误处理

- 统一错误处理策略：API 错误通过 `ElMessage.error` 提示用户
- 禁止静默 `catch` 不反馈：`catch(() => {})`

### 6. 魔法数字

- 防抖间隔等常量集中定义
- 示例：
  ```typescript
  export const DEBOUNCE_SETTINGS = 600  // 阅读设置防抖
  export const DEBOUNCE_PROGRESS = 800  // 进度保存防抖
  export const DEBOUNCE_RESIZE = 150    // resize 防抖
  ```

---

## 通用规范

### 1. 提交

- 提交信息遵循格式：`type: description`
- type 可选：`feat`, `fix`, `docs`, `chore`, `refactor`, `style`
- 示例：`refactor: extract _get_readable_book to service`

### 2. 依赖

- 禁止循环导入
- 依赖流向：API → Service → Model → DB，不反向依赖

