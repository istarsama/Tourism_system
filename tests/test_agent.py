"""
AI ReAct Agent 全链路测试脚本。

测试覆盖：
1) Agent 直接回答（闲聊）→ source 为 "ReAct Agent (AI闲聊)"
2) Agent 调用 RAG 工具 → source 包含 "RAG"
3) Agent 请求未知工具 → 仍能正常完成，不抛出异常
4) run_react_agent max_iterations 阻断 → source 为 "agent_max_iterations_exceeded"

运行方式：
    uv run python tests/test_agent.py
"""

import os
import shutil
import sys
from datetime import datetime

from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from sqlmodel import Session, SQLModel

# ----------------------------------------------------------
# 路径设置
# ----------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# ----------------------------------------------------------
# 测试隔离：使用独立的临时 SQLite + 向量目录
# ----------------------------------------------------------
TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_agent_test.db")
TEST_VECTOR_DIR = os.path.join(PROJECT_ROOT, "tests", "tmp_agent_chroma")

for path in [TEST_DB_PATH]:
    if os.path.exists(path):
        os.remove(path)
if os.path.exists(TEST_VECTOR_DIR):
    shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace(chr(92), '/')}"
os.environ["VECTOR_DB_PATH"] = TEST_VECTOR_DIR.replace("\\", "/")
os.environ["OPENAI_COMPAT_API_KEY"] = "test-key"
os.environ["DEEPSEEK_API_KEY"] = "test-key"
os.environ["EMBEDDING_BACKEND"] = "local_hash"

import ai  # noqa: E402
import ai_agent  # noqa: E402
import api  # noqa: E402
import vector_store  # noqa: E402
from ai_tools import AgentTool, build_all_tools  # noqa: E402
from database import engine  # noqa: E402
from models import SQLModel as _SM  # noqa: E402


# ----------------------------------------------------------
# 本地假 Embedding（不联网，不需要 API Key）
# ----------------------------------------------------------
class FakeEmbeddings(Embeddings):
    def _to_vec(self, text: str) -> list:
        vec = [0.0] * 8
        for idx, ch in enumerate(text):
            vec[idx % 8] += (ord(ch) % 97) / 97.0
        norm = sum(abs(v) for v in vec) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts):
        return [self._to_vec(t) for t in texts]

    def embed_query(self, text: str):
        return self._to_vec(text)


# ----------------------------------------------------------
# 各场景专用 FakeLLM
# ----------------------------------------------------------
class FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLMChat:
    """直接返回 Final Answer，模拟纯闲聊场景（无工具调用）。"""

    def invoke(self, messages):
        return FakeLLMResponse(
            "Thought: 这是纯闲聊，不需要工具。\nFinal Answer: 你好！我是旅游系统助手，有什么可以帮您？"
        )


class FakeLLMRag:
    """先调用 RAG 工具，收到 Observation 后给出 Final Answer。"""

    def invoke(self, messages):
        text = str(messages)
        if "Observation:" in text:
            return FakeLLMResponse(
                "Thought: 已获得检索结果。\nFinal Answer: Agent测试RAG回答内容。"
            )
        return FakeLLMResponse(
            "Thought: 需要查找内部知识。\n"
            "Action: search_internal_knowledge\n"
            "Action Input: 景点推荐"
        )


class FakeLLMUnknownTool:
    """先请求一个不存在的工具，再给出 Final Answer。"""

    def invoke(self, messages):
        text = str(messages)
        if "Observation:" in text:
            return FakeLLMResponse(
                "Thought: 工具不存在，直接回答。\nFinal Answer: 无法调用该工具，但我尽力回答了。"
            )
        return FakeLLMResponse(
            "Thought: 尝试调用工具。\n"
            "Action: non_existent_tool_xyz\n"
            "Action Input: 测试"
        )


class FakeLLMAlwaysLoops:
    """永远请求工具，永不给出 Final Answer，用于触发 max_iterations 阻断。"""

    def invoke(self, messages):
        return FakeLLMResponse(
            "Thought: 还需要更多信息，继续检索。\n"
            "Action: search_internal_knowledge\n"
            "Action Input: 继续查询"
        )


# ----------------------------------------------------------
# 测试用例
# ----------------------------------------------------------
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {name}")
        PASS += 1
    else:
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))
        FAIL += 1


def test_direct_chat(client: TestClient):
    """场景 1：纯闲聊，Agent 直接回答，不调用工具。"""
    print("\n🧪 场景 1：直接闲聊（无工具）")
    ai.chat_llm = FakeLLMChat()
    resp = client.post("/ai/rag_chat", json={"message": "你好"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check(
        "source = AI闲聊",
        "AI闲聊" in data.get("source", ""),
        data.get("source"),
    )


def test_rag_tool(client: TestClient):
    """场景 2：Agent 调用 RAG 工具，source 含 RAG 标签。"""
    print("\n🧪 场景 2：RAG 工具调用")
    ai.chat_llm = FakeLLMRag()
    resp = client.post("/ai/rag_chat", json={"message": "推荐一个好去处"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check(
        "source 含 RAG",
        "RAG" in data.get("source", ""),
        data.get("source"),
    )
    check(
        "reply 含预期文本",
        "Agent测试RAG回答" in data.get("reply", ""),
        data.get("reply", "")[:80],
    )


def test_unknown_tool(client: TestClient):
    """场景 3：Agent 请求不存在的工具，应优雅处理并最终给出回答。"""
    print("\n🧪 场景 3：未知工具优雅处理")
    ai.chat_llm = FakeLLMUnknownTool()
    resp = client.post("/ai/rag_chat", json={"message": "用神秘工具帮我查一下"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空（不崩溃）", bool(data.get("reply")))
    check("有 source 字段", "source" in data)


def test_max_iterations():
    """场景 4：max_iterations 硬限制阻断（直接调用 run_react_agent）。"""
    print("\n🧪 场景 4：max_iterations 强制阻断")
    with Session(engine) as session:
        tools = build_all_tools(
            session=session,
            tavily_client=None,
            current_time=datetime.now().strftime("%Y年%m月%d日"),
        )
    result = ai_agent.run_react_agent(
        llm=FakeLLMAlwaysLoops(),
        tools=tools,
        question="无限循环测试",
        max_iterations=2,
    )
    check(
        "source = agent_max_iterations_exceeded",
        result.get("source") == "agent_max_iterations_exceeded",
        result.get("source"),
    )
    check("reply 非空", bool(result.get("reply")))


def test_empty_message(client: TestClient):
    """场景 5：空 message 请求，应返回 400。"""
    print("\n🧪 场景 5：空 message 校验")
    ai.chat_llm = FakeLLMChat()
    resp = client.post("/ai/rag_chat", json={"message": "   "})
    check("HTTP 400", resp.status_code == 400, str(resp.status_code))


# ----------------------------------------------------------
# 主入口
# ----------------------------------------------------------
def main():
    print("=" * 60)
    print("🤖 ReAct Agent 全链路测试")
    print("=" * 60)

    # 打补丁：使用本地假 Embedding，避免调用真实 API
    vector_store._build_embeddings = lambda: FakeEmbeddings()

    # 初始化数据库表结构（SQLite 临时库）
    SQLModel.metadata.create_all(engine)

    with TestClient(api.app) as client:
        test_direct_chat(client)
        test_rag_tool(client)
        test_unknown_tool(client)
        test_empty_message(client)

    # max_iterations 测试不走 HTTP，直接调用函数
    test_max_iterations()

    # ----------------------------------------------------------
    # 汇总
    # ----------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"测试结果：通过 {PASS}，失败 {FAIL}，共 {PASS + FAIL}")
    print(f"{'='*60}\n")

    if FAIL > 0:
        sys.exit(1)

    # 清理临时文件
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            print(f"⚠️  临时 DB 文件被占用，跳过删除: {TEST_DB_PATH}")
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
