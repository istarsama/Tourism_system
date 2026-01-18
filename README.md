2026/1/18 16:30
## ✨ 核心功能更新 (Key Features)

### 1. 🧠 AI 智能导游 (AI Agent & RAG)
* **DeepSeek 大模型接入**：集成 DeepSeek V3 接口，实现智能对话。
* **RAG (检索增强生成)**：
    * 实现了基于私有数据库的 **RAG Agent**。
    * AI 能自动识别用户意图，提取关键词（如“食堂”、“银杏”）。
    * 自动检索数据库中的日记内容，结合真实数据回答用户提问（如“根据大家反馈，学一食堂好吃吗？”）。
* **日记润色**：利用 LLM 的文学能力，一键美化用户的日记草稿。

### 📂 文件变动
* `src/models.py`: 新增 `Comment` 表，修改 `Diary` 表 (增加 `view_count`, `media_json`, `score` 逻辑)。
* `src/diary.py`: 重构发布接口，新增 `add_comment` (评论并算分)、`search_diaries` (搜索与排序) 接口。
* `src/ai.py`: **[NEW]** 新增 AI 模块，包含 Chat、Polish 和 RAG 检索逻辑。
* `src/upload.py`: **[NEW]** 新增文件上传处理逻辑。
* `src/api.py`: 注册了 AI 和 Upload 路由，增加了静态文件挂载 (`Mount StaticFiles`)。

### 🔌 新增 API 接口一览
| 方法 | 路径 | 描述 |
| :--- | :--- | :--- |
| `POST` | `/ai/rag_chat` | **AI 智能问答** (支持查库) |
| `POST` | `/ai/polish` | **AI 日记润色** |
| `GET` | `/diaries/search` | **全站搜索** (支持 `sort_by=heat/score`) |
| `POST` | `/diaries/comment` | **发表评论** (自动更新日记评分) |
| `GET` | `/diaries/{id}/comments` | **获取评论列表** |
| `POST` | `/upload` | **上传图片/视频** |

################################
2026/1/18 15:50
版本更新：v2.1 - 更新得分算法机制，现在得分系统正常工作
在ai.py中接入了deepseek-v3.2模型，在本地部署时填入API即可
已优化得分计算，现在发布日记后的得分可以正常显示了

################################
2026/1/18 15:00
🚀 版本更新：v2.0 - 核心业务功能上线
日记热度系统 (Hotness System)
数据库升级：Diary 表新增 view_count (浏览量) 字段。
自动统计：实现了日记详情接口 (/detail/{id})，每次访问自动增加浏览量。
推荐算法：实现了基于 “热度优先” 和 “评分优先” 的排序算法，满足个性化推荐需求。
全站搜索与检索 (Search Engine)
实现全文检索接口 (/search)。
支持 or_ 逻辑：可同时在 标题 和 内容 中匹配关键词。
支持搜索结果按热度或时间排序。
多媒体支持 (Multimedia)
文件上传：新增 upload.py 模块，支持图片/视频文件上传到服务器。
静态资源挂载：配置 FastAPI 静态目录，支持通过 URL (/uploads/xxx.jpg) 直接访问图片。
数据库存储：优化 media_json 字段，存储真实的文件路径。
系统稳定性优化
优化 lifespan 生命周期，服务启动时自动检测并修复缺失的数据库表结构。
