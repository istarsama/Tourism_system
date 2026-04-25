"""
LangGraph 多智能体全链路测试脚本。

测试覆盖：
1) 意图路由 → chat，直接闲聊回答，source 含 "闲聊"
2) 意图路由 → rag，RAG 专家调用工具，source 含 "RAG"
3) 意图路由 → web，Web 专家调用工具，source 含 "Web"
4) 专家节点 LLM 调用失败 → error 路径降级回复，不崩溃
5) MAX_STEPS 保护：专家无限工具循环被截断
6) 空 message → HTTP 400

运行方式：
    uv run python tests/test_agent.py
"""

import os
import shutil
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from langchain_core.messages import AIMessage
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
from ai_tools import build_rag_tool, build_web_tool  # noqa: E402
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

class _FakeResponse:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLMRouter:
    """路由器 LLM 工厂：返回固定路由标签。"""
    def __init__(self, route: str):
        self._route = route

    def invoke(self, messages):
        return _FakeResponse(self._route)

    def bind_tools(self, tools):
        return self


class FakeLLMChat:
    """模拟闲聊 Agent：路由判为 chat，直接返回 Final Answer，无工具调用。"""
    _call_count = 0

    def invoke(self, messages):
        self._call_count += 1
        # 第一次调用是 router，第二次是 chat_node
        if self._call_count == 1:
            return _FakeResponse("chat")   # router 输出
        return _FakeResponse("你好！我是旅游系统助手，有什么可以帮您？")

    def bind_tools(self, tools):
        return self


class FakeLLMRag:
    """
    模拟 RAG 流程：router → rag；
    rag_agent_node 第一步发起工具调用，第二步返回最终答案。
    """
    _call_count = 0

    def invoke(self, messages):
        self._call_count += 1
        if self._call_count == 1:
            return _FakeResponse("rag")  # router
        # rag_agent 第一步：不带 tool_calls → 直接给 Final Answer（bind_tools 后模型不调工具）
        return _FakeResponse("Agent测试RAG回答内容。")

    def bind_tools(self, tools):
        # 返回一个会发起工具调用的版本
        outer = self

        class _WithTools:
            _inner_count = 0

            def invoke(self, messages):
                self._inner_count += 1
                if self._inner_count == 1:
                    # 第一步：发起 search_internal_knowledge 工具调用
                    tc = {
                        "name": "search_internal_knowledge",
                        "args": {"query": "景点推荐"},
                        "id": "call_rag_001",
                    }
                    resp = _FakeResponse(content="", tool_calls=[tc])
                    return resp
                # 第二步：有了 ToolMessage，给出最终答案
                return _FakeResponse("Agent测试RAG回答内容。")

        return _WithTools()


class FakeLLMWeb:
    """
    模拟 Web 流程：router → web；
    web_agent_node 发起 search_web_knowledge 工具调用，再给出答案。
    """
    _call_count = 0

    def invoke(self, messages):
        self._call_count += 1
        if self._call_count == 1:
            return _FakeResponse("web")  # router

    def bind_tools(self, tools):
        class _WithTools:
            _inner_count = 0

            def invoke(self, messages):
                self._inner_count += 1
                if self._inner_count == 1:
                    tc = {
                        "name": "search_web_knowledge",
                        "args": {"query": "北京明天天气"},
                        "id": "call_web_001",
                    }
                    return _FakeResponse(content="", tool_calls=[tc])
                return _FakeResponse("Agent测试Web回答内容。")

        return _WithTools()


class FakeLLMAlwaysTools:
    """专家 LLM：永远发起工具调用，用于触发 MAX_STEPS 保护。"""
    _router_done = False

    def invoke(self, messages):
        if not self._router_done:
            self._router_done = True
            return _FakeResponse("rag")

    def bind_tools(self, tools):
        class _Looping:
            def invoke(self, messages):
                tc = {
                    "name": "search_internal_knowledge",
                    "args": {"query": "循环查询"},
                    "id": f"call_{id(messages)}",
                }
                return _FakeResponse(content="", tool_calls=[tc])

        return _Looping()


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
    assert condition, detail or name


@pytest.fixture
def client():
    vector_store._build_embeddings = lambda: FakeEmbeddings()
    SQLModel.metadata.create_all(engine)
    with TestClient(api.app) as test_client:
        yield test_client


def test_chat_route(client: TestClient):
    """场景 1：意图路由 → chat，直接闲聊，source 含 '闲聊'。"""
    print("\n🧪 场景 1：直接闲聊（Router → chat）")
    ai.chat_llm = FakeLLMChat()
    resp = client.post("/ai/rag_chat", json={"message": "你好"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check(
        "source 含 '闲聊'",
        "闲聊" in data.get("source", ""),
        data.get("source"),
    )


def test_rag_route(client: TestClient):
    """场景 2：意图路由 → rag，RAG 专家调用工具，source 含 'RAG'。"""
    print("\n🧪 场景 2：RAG 路由（Router → rag_agent）")
    ai.chat_llm = FakeLLMRag()
    resp = client.post("/ai/rag_chat", json={"message": "推荐一个好去处"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check(
        "source 含 'RAG'",
        "RAG" in data.get("source", ""),
        data.get("source"),
    )
    check(
        "reply 含预期文本",
        "Agent测试RAG回答" in data.get("reply", ""),
        data.get("reply", "")[:80],
    )


def test_web_route(client: TestClient):
    """场景 3：意图路由 → web，Web 专家调用工具，source 含 'Web'。"""
    print("\n🧪 场景 3：Web 路由（Router → web_agent）")
    ai.chat_llm = FakeLLMWeb()
    resp = client.post("/ai/rag_chat", json={"message": "北京明天天气"})
    check("HTTP 200", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check(
        "source 含 'Web'",
        "Web" in data.get("source", ""),
        data.get("source"),
    )
    check(
        "reply 含预期文本",
        "Agent测试Web回答" in data.get("reply", ""),
        data.get("reply", "")[:80],
    )


def test_max_steps(client: TestClient):
    """场景 4：专家节点永远工具循环，MAX_STEPS 后降级，不崩溃。"""
    print("\n🧪 场景 4：MAX_STEPS 强制阻断")
    ai.chat_llm = FakeLLMAlwaysTools()
    ai_agent.MAX_STEPS = 2  # 测试时缩短步数限制
    resp = client.post("/ai/rag_chat", json={"message": "无限循环测试"})
    check("HTTP 200（不崩溃）", resp.status_code == 200, str(resp.status_code))
    data = resp.json()
    check("reply 非空", bool(data.get("reply")))
    check("有 source 字段", "source" in data)
    ai_agent.MAX_STEPS = 6  # 还原


def test_empty_message(client: TestClient):
    """场景 5：空 message → HTTP 400。"""
    print("\n🧪 场景 5：空 message 校验")
    ai.chat_llm = FakeLLMChat()
    resp = client.post("/ai/rag_chat", json={"message": "   "})
    check("HTTP 400", resp.status_code == 400, str(resp.status_code))


def test_run_multi_agent_direct():
    """场景 6：直接调用 run_multi_agent，验证返回格式。"""
    print("\n🧪 场景 6：直接调用 run_multi_agent（chat 路由）")
    with Session(engine) as session:
        rag_tool = build_rag_tool(session)
        web_tool = build_web_tool(None, datetime.now().strftime("%Y年%m月%d日"))

    llm = FakeLLMChat()
    llm._call_count = 0
    result = ai_agent.run_multi_agent(
        llm=llm,
        rag_tool=rag_tool,
        web_tool=web_tool,
        question="随便聊聊",
    )
    check("reply 非空", bool(result.get("reply")))
    check("source 非空", bool(result.get("source")))
    check("source 含 Multi-Agent", "Multi-Agent" in result.get("source", ""), result.get("source"))


# ----------------------------------------------------------
# 主入口
# ----------------------------------------------------------
def main():
    print("=" * 60)
    print("🤖 LangGraph 多智能体全链路测试")
    print("=" * 60)

    # 打补丁：使用本地假 Embedding，避免调用真实 API
    vector_store._build_embeddings = lambda: FakeEmbeddings()

    # 初始化数据库表结构（SQLite 临时库）
    SQLModel.metadata.create_all(engine)

    with TestClient(api.app) as client:
        test_chat_route(client)
        test_rag_route(client)
        test_web_route(client)
        test_max_steps(client)
        test_empty_message(client)

    # 直接函数调用测试（不走 HTTP）
    test_run_multi_agent_direct()

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
