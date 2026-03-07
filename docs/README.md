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

本项目是一个集成了**生成式 AI**、**多维推荐算法**与**社交互动**功能的校园旅游系统。核心亮点在于利用 **RAG (检索增强生成)** 技术，让 AI 能够基于私有的日记数据库回答用户问题，同时具备日记热度统计、动态评分推荐、多媒体分享等完整业务闭环。

## 目录

- [项目简介](#项目简介)
- [核心功能亮点](#核心功能亮点-key-features)
- [API 接口概览](#api-接口概览)
- [项目结构变动](#项目结构变动-file-structure-changes)
- [更新日志](#changelog)

---

## 核心功能亮点 (Key Features)

### 0. 沉浸式拟真导航 (Immersive Navigation)
- **像素级可视化**：不同于传统的地图 API，本项目采用**自定义像素坐标系**。导航路线直接绘制在精美的校园手绘图上，提供沉浸式的视觉体验。
- **智能路径规划**：
    - 内置 **Dijkstra** 与 **多点规划算法**，无论是从 A 到 B，还是顺路去拿个快递，都能规划出最优路线。
    - 支持 **模糊搜索 (Fuzzy Search)**，再也不用担心输错地名找不到路。
- **开发者友好的工具链**：内置 HTML5 地图构建器，无需专业 GIS 知识，点点鼠标即可绘制属于你自己的校园路网。

### 1. AI 智能导游 (AI Agent & RAG)
- **DeepSeek 大模型接入**：集成 DeepSeek V3/V3.2 接口，实现自然语言智能对话。
- **RAG (检索增强生成)**：
    - 实现了基于私有数据库的 **RAG Agent**。
    - **意图识别**：自动分析用户提问，提取核心关键词（如“食堂”、“银杏”）。
    - **知识库问答**：自动检索数据库中的真实日记数据，结合上下文回答用户提问（如“根据大家反馈，学一食堂好吃吗？”）。
- **日记润色**：利用 LLM 的文学能力，一键美化用户的日记草稿，提升内容质量。

### 2. 动态推荐与排序 (Recommendation Engine)
- **热度系统 (Hotness)**：
    - 数据库级原子化更新，用户访问详情页自动增加浏览量 (`view_count`)。
- **多维排序算法**：
    - **热度优先**：基于浏览量的降序排序算法。
    - **评分优先**：基于用户加权平均分的排序算法。
    - **时间倒序**：展示最新发布的动态。
- **全站检索**：支持 `OR` 逻辑的全文模糊检索，可同时匹配标题与内容。

### 3. 社交与多媒体 (Social & Multimedia)
- **动态评分**：摒弃作者自评，采用**用户评论加权平均算法**，实时更新日记得分。
- **文件服务**：支持图片/视频上传，配置静态资源挂载，实现媒体资源的直接访问。

### 4. 进阶 AI Agent (Advanced AI Agent)
- **Tool Use (工具调用)**：
    - 系统内置了 **LocalDB (本地库)** 和 **Internet (互联网)** 两种工具。AI 不再是单纯的文本生成器，而是具备**行动能力**的智能体。
- **混合检索架构 (Hybrid Search)**：
    - 结合了 **RAG (检索增强生成)** 与 **Real-time Search (实时搜索)**。既能回答“食堂好不好吃”（私有数据），也能回答“北京明天冷不冷”（公有数据）。

---

## API 接口概览

| 模块 | 方法 | 路径 | 鉴权 | 描述 |
| :--- | :--- | :--- | :--- | :--- |
| **基础** | `GET` | `/` | 无需 | 服务状态 |
| **地图** | `GET` | `/graph` | 无需 | 地图节点与边数据 |
|  | `GET` | `/spots/list` | 无需 | 获取所有景点（下拉框） |
|  | `GET` | `/spots/search` | 无需 | 景点模糊搜索 |
| **导航** | `POST` | `/navigate` | 无需 | 单点/多点路线规划，返回 `path_coords` |
| **认证** | `POST` | `/auth/register` | 无需 | 用户注册 |
|  | `POST` | `/auth/login` | 无需 | 用户登录，返回 Bearer Token |
| **日记管理** | `POST` | `/diaries/` | 需要 | 发布日记（含媒体链接列表） |
|  | `POST` | `/diaries/comment` | 需要 | 发表评论并更新平均分 |
|  | `GET` | `/diaries/detail/{diary_id}` | 无需 | 获取详情（浏览量 +1） |
|  | `GET` | `/diaries/{diary_id}/comments` | 无需 | 获取评论列表 |
|  | `GET` | `/diaries/spot/{spot_id}` | 无需 | 获取景点日记列表（支持排序） |
|  | `GET` | `/diaries/search` | 无需 | 全站搜索与排序推荐 |
| **AI 智能** | `POST` | `/ai/rag_chat` | 无需 | 问答：本地库 RAG + Tavily 联网搜索路由 |
|  | `POST` | `/ai/polish` | 无需 | 日记润色 |
| **文件服务** | `POST` | `/upload` | 无需 | 上传图片/视频（返回静态 URL） |

---

## 项目结构变动 (File Structure Changes)

本次更新涉及的核心文件修改如下：

- `src/models.py`: 
    -  新增 `Comment` 表。
    -  修改 `Diary` 表 (增加 `view_count`, `media_json`, `score` 字段)。
- `src/diary.py`: 
    -  重构发布接口。
    -  新增 `add_comment` (评论并算分) 与 `search_diaries` (搜索与排序) 接口。
- `src/ai.py` **[NEW]**: 
    -  新增 AI 核心模块，封装 Chat、Polish 和 RAG 检索逻辑。
- `src/upload.py` **[NEW]**: 
    -  新增文件上传处理逻辑。
- `src/api.py`: 
    -  注册 AI 和 Upload 路由。
    -  增加静态文件挂载 (`Mount StaticFiles`)。

---

<a id="changelog"></a>
##  更新日志 (Update Log) - 2026/1/19
###  2026/1/19 - v2.4 正式版：AI Agent 联网与时空感知
- **[Feature] AI 联网搜索 (Internet Search)**：
    - 集成 **Tavily API**，使 DeepSeek 具备访问实时互联网的能力。
    - 解决了大模型无法回答“明天天气”、“最新新闻”等时效性问题的痛点。
- **[Arch] 意图识别路由 (Intent Router)**：
    - 采用 **ReAct (Reasoning + Acting)** 架构，设计了基于 Prompt 的轻量级路由层。
    - AI 能精准判断用户意图：
        -  **校内问题** -> 路由至本地数据库 (RAG)
        -  **校外/实时问题** -> 路由至互联网搜索 (Tavily)
        -  **闲聊** -> 直接回答
- **[Fix] 时空感知 (Temporal Awareness)**：
    - 在 Prompt 中动态注入**系统当前时间**，消除了 AI 的“时间幻觉” (Time Hallucination)，确保天气查询等功能的准确性。

###  22:20 - v2.3 正式版：拟真路线与可视化导航
- **[Map] 自研像素级地图引擎**：
    - 摒弃抽象经纬度，基于真实校园平面图 (`map.png`) 构建 `(x, y)` 像素坐标系，实现“所见即所得”的精准定位。
    - 配套开发 **可视化打点工具 (`map_tool.html`)**，支持鼠标点击快速生成路网 JSON 数据，支持撤销、改名与闭环连接。
- **[Nav] 可视化路径规划**：
    - 后端接口 `/navigate` 升级，新增返回 `path_coords` (像素坐标点集)。
    - 前端支持在地图图片上通过 SVG/Canvas 动态绘制导航红线，直观展示行走路线。
- **[Algo] 高级算法集成**：
    - **多点途经规划**：支持“西门 -> 图书馆 -> 食堂”的 TSP (旅行商问题) 近似路径规划。
    - **模糊地点搜索**：集成 `thefuzz` 库，支持“学一”自动匹配“学一食堂”并定位。
    - **多策略导航**：支持 **步行 (最短距离)** 与 **自行车 (最短时间)** 两种权重策略切换。

### 超级测试工具箱
为了方便开发者调试，项目内置了交互式测试套件。
- **启动方式**: 
  ```bash
  uv run run_tests.py
  ```

### 16:30 - v2.1 正式版：AI 深度集成
- **[Feature]** RAG Agent 上线：AI 现已支持读取私有数据库内容回答问题。
- **[Feature]** 意图识别优化：AI 可精准提取搜索关键词。
- **[Feature]** 日记润色功能上线。

### 15:50 - v2.1 修复版：算法修正
- **[Fix]** 修复评分算法：优化了平均分计算逻辑，现在发布日记及评论后的得分显示正常。
- **[Model]** 模型升级：`ai.py` 接入 DeepSeek-v3.2 模型。

### 15:00 - v2.0 大版本：核心业务上线
- **[Core]** 日记热度系统上线 (View Count)。
- **[Core]** 推荐算法实装 (Heat/Score/Time Sorting)。
- **[Search]** 全文检索引擎上线。
- **[Media]** 图片/视频上传与静态资源托管完成。
- **[System]** 增加 `lifespan` 自动数据库表结构检测与修复。

---

> **快速开始**: 请确保在 `src/ai.py` 中填入有效的 DeepSeek API Key，并运行 `uv run uvicorn src.api:app --reload` 启动服务。
