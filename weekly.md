# 周报 · 校园旅游系统后端重构

**日期**：2026-04-22

---

## 本周工作总结

### 一、后端分层重构（Priority 1）

将原本约 700 行的 `src/api.py` 单体文件拆分为清晰的分层结构：

#### 新增目录与模块

| 目录 | 文件 | 说明 |
|------|------|------|
| `src/routers/` | `spots.py` | `/spots/list`、`/spots/search` 路由 |
| `src/routers/` | `map.py` | `/graph`、`/map/campus-graph`、`/map/mode`、`/map/national-spots` 路由 |
| `src/routers/` | `navigation.py` | `/navigate`（校园 Dijkstra）、`/navigate/osm`（真实路网）路由 |
| `src/routers/` | `xhs.py` | `/plan/xhs_trip` 小红书行程规划路由 |
| `src/services/` | `map_service.py` | 封装 `_global_graph` 与 `_osm_service` 单例，对外暴露 `get_graph()`/`set_graph()`/`get_osm_service()` |
| `src/services/` | `ai_session_service.py` | 会话持久化服务：`get_or_create_session()`、`append_message()`、`generate_session_title()`、`archive_session()` |
| `src/schemas/` | `map.py` | 地图相关 Pydantic 响应模型 |
| `src/schemas/` | `navigation.py` | 导航与 XHS 请求/响应模型 |
| `src/schemas/` | `ai.py` | AI 对话请求/响应、会话管理模型（含 `ChatRequest` 新增 `session_id` 字段） |

#### 改写文件

- **`src/api.py`**：从 700 行精简至约 140 行，仅保留 `lifespan`、应用创建、中间件注册、Router 挂载。新增 `osm_service` 代理对象（`_OsmServiceProxy`）保持测试层对 `api.osm_service` 的直接 mock 兼容性。

---

### 二、AI 会话持久化（Priority 2）

将原本无状态的 `/ai/rag_chat` 接口升级为支持多轮对话记忆：

- **`src/ai.py` 完整改写**：
  - 新增 `get_optional_user()` 依赖（`auto_error=False`），允许匿名用户调用，已登录用户自动绑定会话。
  - `/ai/rag_chat` 增加 `session_id` 参数，每轮问答写入 `ChatSession` / `ChatMessage`，响应中返回 `session_id`。
  - 首轮对话后异步调用 LLM 生成 ≤15 字的中文会话标题（失败静默降级）。
  - 新增 4 个会话管理接口：
    - `POST /ai/sessions`：创建新会话
    - `GET /ai/sessions`：获取当前用户所有会话列表
    - `GET /ai/sessions/{id}/messages`：获取会话消息历史
    - `DELETE /ai/sessions/{id}`：删除会话

---

### 三、测试验证

所有自动化测试（TestClient 模式）全部通过：

| 测试文件 | 结果 |
|----------|------|
| `test_map_api.py` | ✅ 通过 |
| `test_osm_api.py` | ✅ 通过 |
| `test_osm_frontend_contract.py` | ✅ 通过 |
| `test_diary_scope.py` | ✅ 通过 |
| `test_agent.py` | ✅ 通过（18/18） |
| `test_poi_sync.py` | ✅ 通过 |
| `test_search_scope.py` | ✅ 通过 |
| `test_national_spots_link.py` | ✅ 通过 |
| `test_national_spot_schema_upgrade.py` | ✅ 通过 |
| `test_init_db_schema_compat.py` | ✅ 通过 |

---

## 下周计划

| 优先级 | 内容 |
|--------|------|
| P3 | 统一地点体系：校园 spot 与 national spot 均映射到 `POI` 主键，`Diary` 最终只关联 `poi_id` |
| P4 | 工程化基础设施：Alembic 迁移替代启动补列、配置分层（dev/test/prod）、限流与防刷 |
| P5 | 推荐与搜索优化：热度衰减、评论数加权、个性化推荐 |
