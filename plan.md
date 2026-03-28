# Tourism System 重构计划（LangChain + ChromaDB）

## 1. 目标概述

本轮重构目标是在**不改前端**的前提下，完成后端 AI 能力升级：

- 引入 LangChain 与 ChromaDB，建立标准 RAG 流水线。
- 将历史 MySQL 数据（游记/景点）向量化并灌入本地向量库。
- 对新增游记实现 MySQL + 向量库增量双写。
- 重构 `src/ai.py`：先向量检索，再按 `mysql_id` 回查 MySQL，再生成回答。
- 可选进阶：引入 Tool Calling Agent，统一内部知识检索与外部 Tavily 检索。

已确认策略：

- Embedding 采用 **OpenAI 兼容 API**。
- 双写失败时：**MySQL 成功，向量写入失败仅记录日志**，不阻塞主流程。
- `/ai/rag_chat` 暂时保持**非流式 JSON 返回**，确保前端无改动可继续使用。

---

## 2. 当前状态（已完成分析）

- 依赖管理：`pyproject.toml` + `uv`，当前尚未引入 LangChain/ChromaDB 依赖。
- AI 现状：`src/ai.py` 使用 `AsyncOpenAI + Tavily`，已有简化版路由，但非向量 RAG。
- 数据源：`Diary`、`NationalSpot` 已可作为向量化输入。
- 写入链路：`src/diary.py` 仅写 MySQL，无向量库同步。
- 测试方式：脚本式执行（`uv run python tests/<script>.py` / `uv run run_tests.py`）。

---

## 3. 分阶段实施计划（拆分小目标）

### 阶段 A：依赖与配置更新

1. 修改 `pyproject.toml`，新增：
   - `langchain`
   - `langchain-core`
   - `langchain-openai`
   - `chromadb`
2. 增加向量与 Embedding 配置读取约定：
   - `VECTOR_DB_PATH`
   - `OPENAI_COMPAT_BASE_URL`
   - `OPENAI_COMPAT_API_KEY`
   - `EMBEDDING_MODEL`
3. 执行依赖安装与导入验证。

交付物：

- 依赖更新后的 `pyproject.toml`
- 可导入验证通过

---

### 阶段 B：历史数据灌入向量库

1. 新增 `tools/init_vector_db.py`（一次性初始化脚本）。
2. 脚本实现：
   - 读取 MySQL 的 `Diary` 与 `NationalSpot`
   - 拼装文档文本（标题、正文、城市、类型等）
   - 调用 Embedding API
   - 写入 ChromaDB
3. 规范 metadata：
   - `{"mysql_id": <真实ID>, "type": "diary"|"national_spot"}`
4. 使用稳定文档 ID（如 `diary:<id>` / `spot:<id>`）实现幂等重跑。

交付物：

- `tools/init_vector_db.py`
- 可重复执行且不会重复脏写的向量化脚本

---

### 阶段 C：新增数据双写同步

1. 在 `src/diary.py` 的创建日记成功提交后，追加向量 upsert。
2. 建议新增 `src/vector_store.py` 统一封装：
   - Chroma 客户端初始化
   - 文档构建
   - Embedding 调用
   - upsert 方法
3. 错误处理遵循已确认策略：
   - MySQL 已提交即返回成功
   - 向量写入失败记录日志，便于后续补偿

交付物：

- `src/diary.py` 双写逻辑
- `src/vector_store.py`（或等价封装）

---

### 阶段 D：重构 AI 核心为 LangChain RAG

1. 重构 `src/ai.py`，使用 `ChatOpenAI`。
2. 接入 Chroma Retriever，相似度检索得到候选 metadata。
3. 提取 `mysql_id/type` 回查 MySQL 完整数据。
4. 用 `PromptTemplate` 拼接上下文，生成回答。
5. 保持接口兼容：
   - 路由不变：`/ai/rag_chat`
   - 返回格式保持 JSON（`reply`, `source`）

交付物：

- 重构后的 `src/ai.py`
- 与前端兼容的返回结构

---

### 阶段 E（进阶）：Agent + Tool Calling 路由

1. 封装两个工具：
   - 内部工具：向量检索 + MySQL 回查
   - 外部工具：Tavily 搜索
2. 使用 LangChain Tool Calling Agent 自动决策调用路径。
3. 失败降级与来源标识完善（`source` 可追踪）。

交付物：

- 支持工具路由的 AI 模块（`src/ai.py`）

---

## 4. 涉及文件清单

- 修改：`pyproject.toml`
- 新增：`tools/init_vector_db.py`
- 新增（建议）：`src/vector_store.py`
- 修改：`src/diary.py`
- 重构：`src/ai.py`
- 可选更新：`tests/test_ai.py`、`tests/test_rag.py`（或新增脚本测试）

---

## 5. 验证清单（完成标准）

1. 依赖验证：LangChain/Chroma 可成功导入。
2. 历史灌入验证：脚本运行后，Chroma 文档包含 `mysql_id/type`。
3. 双写验证：发布新日记后，MySQL 与向量库均可看到对应数据。
4. RAG 验证：`/ai/rag_chat` 能基于内部数据回答；外部问题能走 Tavily。
5. 回归验证：现有脚本测试通过，不影响前端现有调用。

---

## 6. 风险与注意事项

- Embedding API 的速率/费用需关注，必要时增加批处理与重试节流。
- 双写是“最终一致性”策略，建议后续补一个离线补偿脚本。
- 若未来改流式响应，需要单独版本控制并提前评估前端兼容性。
