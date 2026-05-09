# Tourism System 前后端对接与项目脉络

> 文件名沿用当前要求：`fronted to back.md`。  
> 本文面向前端、后端和联调同学，说明项目整体结构、后端模块、前后端接口契约、测试策略和后续开发边界。

## 1. 项目总体定位

本项目是一个校园旅游与日记分享系统，当前核心形态是：

- 前端：Vue 3 + Vite + Pinia + Axios
- 后端：FastAPI + SQLModel/SQLAlchemy
- 数据库：PostgreSQL 16 + PostGIS 3.4，Docker Compose 本地部署
- AI：OpenAI-Compatible/DeepSeek + LangGraph + LangChain Tools + Chroma
- 地图：校园自定义像素地图 + 全国 OSM 地图

主要功能包括：

- 用户注册、登录、JWT 鉴权
- 校园地图展示、景点搜索、Dijkstra 路径规划
- 全国景点展示、同城 OSM 路网导航
- 旅游日记发布、浏览、评论、评分、排序、搜索
- 图片/视频上传
- AI 导游问答、RAG 检索、联网搜索、日记润色
- 小红书数据抓取、清洗、下载、导入
- POI 统一地点体系第一阶段
- Alembic 数据库迁移

## 2. 目录结构

```text
Tourism_system/
├─ src/                    # 后端核心代码
│  ├─ api.py               # FastAPI 应用入口、路由挂载、生命周期
│  ├─ auth.py              # 用户注册、登录、JWT 鉴权
│  ├─ diary.py             # 日记、评论、搜索、评分
│  ├─ ai.py                # AI 对话、日记润色、会话管理
│  ├─ ai_agent.py          # LangGraph 多智能体编排
│  ├─ ai_tools.py          # RAG/Web 工具封装
│  ├─ database.py          # 数据库连接、兼容补列
│  ├─ models.py            # SQLModel 数据模型
│  ├─ poi_service.py       # POI 统一地点体系
│  ├─ vector_store.py      # Chroma 向量库封装
│  ├─ routers/             # 地图、导航、景点、小红书计划等路由
│  ├─ services/            # 地图服务、AI 会话服务
│  ├─ schemas/             # 请求/响应模型
│  └─ tools/Spider_XHS/    # 小红书爬虫工具
├─ frontend/               # 前端 Vue 项目
├─ tests/                  # 自动化测试与手动联调脚本
├─ tools/                  # 后端脚本工具：导入、初始化、查看数据库等
├─ alembic/                # Alembic 迁移脚本
├─ docs/                   # 项目文档
├─ docker/                 # PostgreSQL/PostGIS 初始化 SQL
├─ data/                   # 校园地图、种子数据、静态资源
├─ uploads/                # 用户上传文件，运行期生成
├─ docker-compose.yml      # 本地 PostgreSQL/PostGIS
└─ pyproject.toml          # 依赖与 pytest 配置
```

## 3. 当前运行方式

### 启动数据库

```bash
docker compose up -d
```

默认数据库：

```env
DATABASE_URL=postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav
```

### 执行迁移

```bash
uv run alembic upgrade head
```

当前迁移进度：

- `0001_baseline_current_models.py`：按当前 SQLModel 元数据创建基线表结构
- `0002_diary_poi_id.py`：为 `diary` 增加统一地点字段 `poi_id`

### 启动后端

```bash
uv run uvicorn src.api:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

### 启动前端

```bash
cd frontend
npm run dev
```

前端通过 `VITE_API_BASE` 配置后端地址；如果前后端同源部署，可为空。

## 4. 前端 API 封装现状

前端统一入口：

```text
frontend/src/api/index.js
```

Axios 配置：

- `baseURL = import.meta.env.VITE_API_BASE || ''`
- 超时：30 秒
- 自动从 `localStorage.token` 注入：

```http
Authorization: Bearer <token>
```

统一错误处理：

- 优先读取 `error.response.data.detail`
- 否则使用 `error.message`

## 5. 后端模块脉络

### 应用入口

文件：

```text
src/api.py
```

职责：

- 初始化数据库表结构
- 初始化地图配置
- 同步全国景点到 POI
- 加载校园地图
- 同步校园景点到 POI
- 回填历史日记 `poi_id`
- 挂载静态文件 `/uploads`、`/data`
- 注册各业务路由
- 如果存在 `frontend-dist/`，挂载前端构建产物

### 数据库模型

文件：

```text
src/models.py
```

核心表：

- `User`：用户
- `Diary`：日记，现已增加 `poi_id`
- `Comment`：评论和评分
- `POI`：统一地点主表
- `POIAlias`：地点别名
- `POIGeometry`：地点坐标
- `NationalSpot`：全国景点
- `NationalSpotXHSNote`：小红书预览
- `MapConfig`：地图模式配置
- `ChatSession` / `ChatMessage` / `MemoryItem`：AI 会话与记忆
- `RouteCache`：路线缓存预留

### POI 统一地点体系

当前处于兼容阶段。

旧字段仍保留：

- `Diary.spot_id`：校园景点
- `Diary.national_spot_id`：全国景点

新字段：

- `Diary.poi_id`：统一地点主键

写入规则：

- `scope=campus` 时通过 `spot_id` 找 `POI(source="campus")`
- `scope=national` 时通过 `national_spot_id` 找 `POI(source="national_spot")`
- 创建日记时自动写入 `poi_id`
- 启动时自动回填历史日记

后续推荐方向：

1. 前端仍可继续传旧字段，保证兼容。
2. 新接口可逐步增加 `poi_id` 入参。
3. 后端查询逐步改为优先 `poi_id`，旧字段 fallback。

## 6. API 对接总览

### 基础状态

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 后端运行状态 |

返回：

```json
{
  "status": "ok",
  "message": "校园旅游系统后端正在运行"
}
```

### 用户认证

| 方法 | 路径 | 是否登录 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | 否 | 注册 |
| POST | `/auth/login` | 否 | 登录并返回 JWT |

注册请求：

```json
{
  "username": "alice",
  "password": "123456"
}
```

登录返回：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "msg": "登录成功！"
}
```

前端处理：

- 登录成功后把 `access_token` 存入 `localStorage.token`
- 用户名存入 `localStorage.user`
- 后续请求由 Axios 自动附带 Authorization

### 地图与景点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/graph` | 校园地图节点和边 |
| GET | `/map/campus-graph` | `/graph` 兼容别名 |
| GET | `/map/mode?scope=campus` | 校园地图模式配置 |
| GET | `/map/mode?scope=national` | 全国地图模式配置 |
| GET | `/map/national-spots` | 全国景点点位 |
| GET | `/spots/list` | 校园景点列表 |
| GET | `/spots/search` | 校园/全国景点搜索 |

`GET /graph` 返回：

```json
{
  "nodes": [
    {
      "id": 44,
      "name": "学生食堂",
      "type": "spot",
      "x": 123.0,
      "y": 456.0,
      "desc": "..."
    }
  ],
  "edges": [
    {
      "u": 1,
      "v": 2,
      "distance": 30.0
    }
  ]
}
```

`GET /spots/search` 参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `query` | string | 必填 | 搜索关键词 |
| `limit` | int | 5 | 返回数量，1-20 |
| `scope` | string | campus | `campus` 或 `national` |
| `city` | string | 可选 | national 模式城市过滤 |

national 搜索返回含：

```json
{
  "id": 1,
  "name": "故宫",
  "city": "北京",
  "type": "历史遗迹",
  "latitude": 39.916345,
  "longitude": 116.397155,
  "scope": "national"
}
```

### 导航

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/navigate` | 校园路径规划 |
| POST | `/navigate/osm` | 全国同城 OSM 路网导航 |

校园导航请求：

```json
{
  "start_id": 1,
  "end_id": 44,
  "via_ids": [],
  "strategy": "dist",
  "transport": "walk"
}
```

字段说明：

- `strategy=dist`：最短距离
- `strategy=time`：按速度和拥挤度估算最短时间
- `transport=walk`：步行
- `transport=bike`：骑行
- `via_ids` 不为空时走多点贪心规划

校园导航返回：

```json
{
  "path_ids": [1, 2, 44],
  "path_names": ["A", "B", "学生食堂"],
  "path_coords": [[10, 20], [30, 40], [50, 60]],
  "total_cost": 120.5,
  "cost_unit": "米"
}
```

OSM 导航请求：

```json
{
  "start_spot_id": 1,
  "end_spot_id": 2,
  "transport": "walk"
}
```

限制：

- 只支持同城市全国景点
- `transport` 仅支持 `walk`、`bike`

返回：

```json
{
  "city": "北京",
  "transport": "walk",
  "start_spot_id": 1,
  "end_spot_id": 2,
  "node_ids": [100, 101, 102],
  "path_coords": [[39.9, 116.3], [39.91, 116.31]],
  "total_distance_m": 12800.5,
  "segment_count": 2,
  "segment_distances_m": [6000.0, 6800.5],
  "estimated_duration_s": 9143.21
}
```

### 日记与评论

| 方法 | 路径 | 是否登录 | 说明 |
|---|---|---|---|
| POST | `/diaries/` | 是 | 发布日记 |
| GET | `/diaries/detail/{diary_id}` | 否 | 日记详情，浏览量 +1 |
| GET | `/diaries/{diary_id}/comments` | 否 | 评论列表 |
| POST | `/diaries/comment` | 是 | 发表评论并更新平均分 |
| GET | `/diaries/spot/{spot_id}` | 否 | 某景点日记列表 |
| GET | `/diaries/search` | 否 | 全站日记搜索/推荐 |

创建校园日记：

```json
{
  "scope": "campus",
  "spot_id": 44,
  "title": "食堂体验",
  "content": "早餐种类很多。",
  "media_files": ["/uploads/a.jpg"]
}
```

创建全国景点日记：

```json
{
  "scope": "national",
  "national_spot_id": 1,
  "title": "故宫赏花",
  "content": "春天很适合去。",
  "media_files": []
}
```

日记返回字段：

```json
{
  "id": 1,
  "poi_id": 10,
  "spot_id": 44,
  "scope": "campus",
  "national_spot_id": null,
  "user_name": "alice",
  "title": "食堂体验",
  "content": "早餐种类很多。",
  "score": 0.0,
  "view_count": 0,
  "media_files": [],
  "created_at": "2026-05-09T12:00:00"
}
```

评论请求：

```json
{
  "diary_id": 1,
  "content": "写得很好",
  "score": 5.0
}
```

搜索参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `keyword` | string | 可选 | 搜索标题或正文 |
| `sort_by` | string | heat | `heat`、`score`、`latest` |
| `scope` | string | all | `all`、`campus`、`national` |

### 文件上传

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/upload` | 上传图片/视频到本地 `uploads/` |

请求：

```http
Content-Type: multipart/form-data
file=<binary>
```

返回：

```json
{
  "filename": "origin.jpg",
  "url": "/uploads/uuid.jpg"
}
```

前端把返回的 `url` 放入日记的 `media_files`。

### AI

| 方法 | 路径 | 是否登录 | 说明 |
|---|---|---|---|
| POST | `/ai/rag_chat` | 可选 | AI 问答，登录时持久化会话 |
| POST | `/ai/polish` | 否 | 日记润色 |
| POST | `/ai/sessions` | 是 | 创建会话 |
| GET | `/ai/sessions` | 是 | 会话列表 |
| GET | `/ai/sessions/{id}/messages` | 是 | 会话消息 |
| DELETE | `/ai/sessions/{id}` | 是 | 归档会话 |

当前前端封装：

```js
chatWithAI: (message) => apiClient.post('/ai/rag_chat', { message })
```

后端已支持：

```json
{
  "message": "推荐一下食堂",
  "session_id": "可选"
}
```

返回：

```json
{
  "reply": "...",
  "source": "Multi-Agent (内部旅游专家 RAG)",
  "session_id": "..."
}
```

注意：

- 未登录也可问答，但 `session_id` 为 `null`
- 登录后不传 `session_id` 会自动创建新会话
- 当前前端还没有完整消费 AI 会话列表和历史消息，可作为后续联调点

### 小红书与全国景点预览

小红书相关主要是后端脚本/导入能力，前端主要消费全国景点接口中的预览字段：

```json
{
  "xhs_query": "北京 故宫 海棠",
  "xhs_note_count": 3,
  "xhs_fetch_status": "success",
  "xhs_fetch_message": "已同步 3 条小红书帖子预览。",
  "xhs_cookie_needs_refresh": false,
  "xhs_notes_preview": [
    {
      "note_id": "...",
      "title": "...",
      "content_preview": "...",
      "thumbnail_url": "...",
      "xhs_url": "...",
      "author_name": "...",
      "likes": 128
    }
  ]
}
```

后端最近修复：

- `Spider_XHS` 能爬到数据但不下载的问题
- `save_choice=all/media/excel` 的保存逻辑
- 小红书媒体下载请求头和超时
- 旧 `crawler.py` 对 `nickname/user_id/liked_count/image_list` 的字段兼容

## 7. 前端 Store 对接关系

### `useAuthStore`

文件：

```text
frontend/src/stores/auth.js
```

职责：

- 保存 token
- 保存 username
- 登录状态判断
- 清除登录态

后端接口：

- `/auth/register`
- `/auth/login`

### `useMapStore`

文件：

```text
frontend/src/stores/map.js
```

职责：

- 校园地图节点/边
- 校园景点搜索
- 校园路径规划
- 当前起点、终点、路径和选中景点

后端接口：

- `/graph`
- `/spots/search?scope=campus`
- `/navigate`

### `useNationalMapStore`

文件：

```text
frontend/src/stores/nationalMap.js
```

职责：

- 全国地图配置
- 全国景点列表
- 选中景点、起点、终点
- OSM 路线结果

后端接口：

- `/map/mode?scope=national`
- `/map/national-spots`
- `/navigate/osm`

### `useDiaryStore`

文件：

```text
frontend/src/stores/diary.js
```

职责：

- 日记列表
- 日记详情
- 评论列表
- 创建日记
- 添加评论

后端接口：

- `/diaries/search`
- `/diaries/spot/{spot_id}`
- `/diaries/detail/{diary_id}`
- `/diaries/`
- `/diaries/{diary_id}/comments`
- `/diaries/comment`

## 8. 前后端联调注意事项

### 认证

需要登录的接口：

- `POST /diaries/`
- `POST /diaries/comment`
- `POST /ai/sessions`
- `GET /ai/sessions`
- `GET /ai/sessions/{id}/messages`
- `DELETE /ai/sessions/{id}`

前端必须带：

```http
Authorization: Bearer <token>
```

### 日记 scope

创建日记时必须区分：

- 校园：`scope=campus` + `spot_id`
- 全国：`scope=national` + `national_spot_id`

不要同时传两个地点 ID。后端会自动解析 `poi_id`。

### 全国地图坐标

OSM 返回的 `path_coords` 格式为：

```text
[[lat, lng], [lat, lng]]
```

前端如果使用 Leaflet/地图组件，通常可以直接消费。

校园地图坐标是像素坐标：

```text
[[x, y], [x, y]]
```

两套坐标系统不要混用。

### AI 会话

当前前端只调用：

```js
api.chatWithAI(message)
```

如果要做多会话：

1. 登录后调用 `/ai/sessions` 获取会话列表。
2. 点选会话后调用 `/ai/sessions/{id}/messages`。
3. 发消息时传 `{ message, session_id }`。
4. 接收返回的 `session_id` 并更新当前会话。

### 小红书预览

前端不需要直接调用爬虫。全国景点接口已经返回预览字段。  
如果 `xhs_cookie_needs_refresh=true`，表示后端 Cookie 失效，应提示后端更新 `.env` 中的 `XHS_COOKIE`。

## 9. 测试策略和清理说明

现在项目已经使用 `pytest`，命令是：

```bash
uv run python -m pytest -q
```

但 `tests/` 下有两类文件：

### 1. 自动化 pytest 用例

当前 pytest 只收集这些标准化文件：

- `tests/test_agent.py`
- `tests/test_xhs_download_save.py`
- `tests/tools/test_data_length.py`

这些文件必须保留，是 CI/回归测试的基础。

### 2. 手动联调脚本

以下文件虽然放在 `tests/`，但更像“启动后端后手动跑的联调脚本”：

- `tests/test_register.py`
- `tests/test_login.py`
- `tests/test_comment.py`
- `tests/test_flow.py`
- `tests/test_ai.py`
- `tests/test_rag.py`
- 以及多数 `test_map_api.py`、`test_osm_api.py` 等历史脚本

它们仍有价值：

- 适合课堂演示
- 适合手动验证真实后端服务
- 适合联调时快速复现接口问题

但它们不再由 pytest 默认收集，避免导入时修改环境变量或生成临时数据库。

### 清理规则

已经从仓库中清理并忽略：

- `tests/tmp_*.db`
- `tests/tmp_chroma_test/`
- `tests/tmp_agent_chroma/`
- `data/chroma/`
- `__pycache__/`

这些都是运行产物，不应该提交。  
如需恢复向量库，运行：

```bash
uv run python tools/init_vector_db.py
```

## 10. 推荐开发流程

### 后端改动后

```bash
uv run python -m pytest -q
uv run alembic upgrade head
```

如果改了数据库模型：

1. 修改 `src/models.py`
2. 新增 Alembic 迁移
3. 保持 `database.py` 的旧库兼容逻辑，直到确认所有本地库已迁移
4. 更新本文档相关接口字段

### 前端改动后

```bash
cd frontend
npm run dev
```

联调前确认：

- `VITE_API_BASE` 是否指向后端
- token 是否正常保存到 `localStorage.token`
- 日记 scope 是否传对
- national 地图坐标是否按 `[lat, lng]` 使用

## 11. 当前后续重点

1. 前端接入 AI 会话管理。
2. 日记创建逐步支持直接传 `poi_id`。
3. 上传接口增加文件类型、大小限制。
4. 日记和全国景点列表增加分页。
5. 推荐系统从简单排序升级为热度衰减、评论数权重、评分综合。
6. OSM 路线缓存接入 `RouteCache`。
7. 小红书导入流程增加可视化状态和错误提示。
8. 将手动联调脚本逐步改造成标准 pytest，减少 `tests/` 中脚本混杂。
