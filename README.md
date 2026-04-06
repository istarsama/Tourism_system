<div align="center">
  <img src="data/xiaohui.jpg" width="120" alt="School Logo" style="border-radius: 50%; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>

  <h1>校园旅游与日记分享系统</h1>
  <h3>Campus Tourism & Diary System</h3>
  
  <p>
    <b>基于 DeepSeek 大模型的个性化旅游导览与社交平台</b>
    <br/>
    <i>Data Structure Course Design | Powered by FastAPI & DeepSeek V3</i>
  </p>

  <br/>
  <img src="data/map.png" width="100%" alt="Project Map" style="border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.2);"/>
  <br/>
  <br/>

  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  </a>
  <a href="https://fastapi.tiangolo.com/">
    <img src="https://img.shields.io/badge/FastAPI-0.109%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  </a>
  <a href="https://www.deepseek.com/">
    <img src="https://img.shields.io/badge/AI-DeepSeek%20V3-purple?style=for-the-badge&logo=openai&logoColor=white" alt="DeepSeek">
  </a>
  <a href="#">
    <img src="https://img.shields.io/badge/Tech-RAG%20Agent-orange?style=for-the-badge" alt="RAG">
  </a>
</div>
---

## 项目简介

这是一个围绕 **校园导览 + 旅游日记 + AI 问答** 构建的全栈项目。它不是简单的课程作业展示页，而是把地图导航、内容社区、RAG 检索、多智能体路由和数据库工程化改造放在一起，做成了一个可继续迭代的系统。

当前版本已经完成 **MySQL -> PostgreSQL/PostGIS** 迁移，并将数据库以 **Docker 隔离容器** 的方式部署，为后续空间查询、记忆持久化与会话隔离预留了能力。

## 一眼看点

| 模块 | 亮点 |
| :--- | :--- |
| **地图导航** | 校园像素坐标地图，不是套第三方地图 API 的“假导航” |
| **AI 能力** | LangGraph 多智能体 + RAG + 联网搜索 |
| **内容社区** | 日记、评论、评分、浏览量、排序推荐形成完整闭环 |
| **数据库** | PostgreSQL 16 + PostGIS 3.4，Docker 独立部署 |
| **可扩展性** | 已为会话持久化、长期记忆、空间检索预留结构 |

## 核心功能

### 1. 沉浸式校园导航

- 基于自定义校园平面图与像素坐标系
- 支持 Dijkstra 最短路与多点路线规划
- 支持地点模糊搜索
- 前端可直接绘制路线，实现更接近真实校园导览的体验

### 2. AI 导游与 RAG 问答

- 接入 DeepSeek / OpenAI-Compatible 大模型
- LangGraph 多智能体路由：Router / RAG Agent / Web Agent
- 内部知识使用 **向量检索 -> `db_id` 主库回查**
- 支持旅游问答、实时信息补充、日记润色

### 3. 日记社区与推荐系统

- 发布校园/全国景点日记
- 评论后自动更新平均分
- 详情页浏览量自动累加
- 支持热度、评分、时间三种排序逻辑
- 支持关键词搜索与 `scope` 范围过滤

### 4. 全国景点与 OSM 扩展

- 提供全国景点列表、过滤和日记联动
- 支持同城景点 OSM 导航
- 已为 PostGIS 空间能力预留后续扩展空间

### 5. 爬虫导入与知识积累

- 集成小红书 Spider 工具链
- 支持爬取、清洗、景点匹配、导入数据库
- 可作为 RAG 的真实用户评价语料来源

## 系统架构

```mermaid
flowchart LR
    U[User / Frontend] --> API[FastAPI]
    API --> NAV[Navigation Engine]
    API --> DB[(PostgreSQL + PostGIS)]
    API --> VDB[(Chroma Vector DB)]
    API --> AGENT[LangGraph Multi-Agent]
    AGENT --> RAG[RAG Agent]
    AGENT --> WEB[Web Agent]
    AGENT --> CHAT[Direct Chat]
    RAG --> VDB
    RAG --> DB
    WEB --> LLM[LLM]
    CHAT --> LLM
    RAG --> LLM
```

## 技术栈

| 层级 | 技术 |
| :--- | :--- |
| **后端** | FastAPI, SQLModel, SQLAlchemy |
| **数据库** | PostgreSQL 16, PostGIS 3.4, Docker Compose |
| **AI 编排** | LangGraph, LangChain Tools |
| **向量检索** | Chroma |
| **模型接入** | DeepSeek / OpenAI-Compatible API |
| **实时搜索** | Tavily |
| **算法** | Dijkstra, 模糊搜索, 推荐排序 |

## 快速开始

### 1. 启动 PostgreSQL / PostGIS

```bash
docker compose up -d
```

默认数据库配置：

```env
DATABASE_URL=postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav
```

### 2. 安装依赖

```bash
uv sync
```

### 3. 配置 `.env`

至少确认以下环境变量：

```env
DATABASE_URL=postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav
SECRET_KEY=your-secret-key
DEEPSEEK_API_KEY=your-deepseek-api-key
TAVILY_API_KEY=your-tavily-api-key
XHS_COOKIE=your-xiaohongshu-cookie
```

如果只想本地离线调试向量链路，可增加：

```env
EMBEDDING_BACKEND=local_hash
```

### 4. 启动后端

```bash
uv run uvicorn src.api:app --reload
```

服务默认地址：

```text
http://127.0.0.1:8000
```

### 5. 初始化可选数据

初始化全国景点：

```bash
uv run tools/init_national_spots.py
```

初始化全国赏花景点并抓取小红书预览：

```bash
uv run python tools/import_national_flower_spots.py
uv run python tools/crawl_flower_spots.py --city 武汉
```

初始化向量库：

```bash
uv run python tools/init_vector_db.py
```

## 常用命令

| 用途 | 命令 |
| :--- | :--- |
| 启动数据库 | `docker compose up -d` |
| 查看数据库状态 | `docker compose ps` |
| 启动后端 | `uv run uvicorn src.api:app --reload` |
| 打开测试工具箱 | `uv run python run_tests.py` |
| 查看数据库 | `uv run python tools/view_database.py` |
| 初始化全国景点 | `uv run tools/init_national_spots.py` |
| 初始化全国赏花景点并抓取小红书预览 | `uv run python tools/import_national_flower_spots.py` |
| 按城市抓取赏花景点 | `uv run python tools/crawl_flower_spots.py --city 武汉` |
| 初始化向量库 | `uv run python tools/init_vector_db.py` |

## API 概览

| 模块 | 路径 | 说明 |
| :--- | :--- | :--- |
| **基础状态** | `/` | 服务状态 |
| **地图** | `/graph`, `/map/campus-graph`, `/map/mode`, `/map/national-spots` | 校园/全国景点地图能力 |
| **景点搜索** | `/spots/list`, `/spots/search` | 景点列表与模糊搜索 |
| **导航** | `/navigate`, `/navigate/osm` | 校园路径规划与 OSM 导航 |
| **认证** | `/auth/register`, `/auth/login` | 注册与登录 |
| **日记** | `/diaries/*` | 发布、评论、详情、搜索 |
| **AI** | `/ai/rag_chat`, `/ai/polish` | RAG 问答与日记润色 |
| **文件上传** | `/upload` | 图片/视频上传 |

## 当前迁移状态

本次数据库改造已经落地完成：

- 默认数据库已切换为 PostgreSQL/PostGIS
- `pymysql` 已替换为 `psycopg`
- Docker 中隔离部署数据库容器
- MySQL 方言脚本已改写为 PostgreSQL 兼容实现
- 已加入会话/记忆相关表结构，为后续持久化能力铺路

前端或队友本地换库说明见：[`docs/DB_MIGRATION_GUIDE.md`](docs/DB_MIGRATION_GUIDE.md)

## 项目结构

```text
Tourism_system/
├─ src/                    # 后端核心代码
├─ frontend/               # 前端页面
├─ tests/                  # 自动化测试
├─ tools/                  # 导入、初始化、调试工具
├─ docs/                   # 项目文档
├─ docker/                 # PostgreSQL/PostGIS 初始化脚本
├─ data/                   # 地图、向量库、静态数据
├─ docker-compose.yml      # 本地数据库编排
└─ run_tests.py            # 交互式测试工具箱
```

## 文档导航

- [快速开始](docs/QUICK_START.md)
- [数据库迁移指南](docs/DB_MIGRATION_GUIDE.md)
- [爬虫导入指南](docs/CRAWL_IMPORT_GUIDE.md)
- [项目结构说明](docs/PROJECT_STRUCTURE.md)
- [常见问题排查](docs/QUICK_FIX.md)

## 后续规划

- 建立正式的 schema migration 机制
- 补齐历史业务数据迁移脚本
- 为全国景点加入 geometry 列与空间索引
- 持续完善会话隔离与长期记忆能力
