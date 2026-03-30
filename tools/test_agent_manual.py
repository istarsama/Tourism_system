"""
ReAct Agent 手动测试脚本（需要后端服务正在运行）。

用途：在本地验证改造后的 AI Agent 对话行为，支持三种场景：
- 闲聊：Agent 直接回答，不调用工具
- 内部知识检索：Agent 调用 RAG 工具查询景点/日记
- 实时信息：Agent 调用 Tavily 联网搜索（需配置 TAVILY_API_KEY）

运行方式：
    # 先启动后端服务：
    cd src && uv run uvicorn api:app --reload
    # 再运行本脚本：
    uv run python tools/test_agent_manual.py
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")

try:
    import requests
except ImportError:
    print("需要安装 requests：uv add requests")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 60  # ReAct 循环可能多轮调用，给足够的超时时间


def _divider():
    print("-" * 60)


def test_scenario(name: str, question: str, expected_in_source: str):
    """发起一次对话请求并打印结果，验证 source 是否包含预期关键词。"""
    _divider()
    print(f"🧪 场景：{name}")
    print(f"   ❓ 提问：{question}")

    try:
        resp = requests.post(
            f"{BASE_URL}/ai/rag_chat",
            json={"message": question},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        print("   ❌ 连接失败：请确认后端服务已启动（cd src && uv run uvicorn api:app --reload）")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时（>{TIMEOUT}s），可能 Agent 循环次数过多或 LLM 响应慢")
        return False

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    data = resp.json()
    reply = data.get("reply", "")
    source = data.get("source", "（无来源）")

    print(f"   🤖 回复：{reply[:120]}{'...' if len(reply) > 120 else ''}")
    print(f"   📌 来源：{source}")

    ok = expected_in_source in source
    if ok:
        print(f"   ✅ 来源校验通过（含 '{expected_in_source}'）")
    else:
        print(f"   ⚠️  来源不符（预期含 '{expected_in_source}'，实际：'{source}'）")
    return ok


def test_polish(text: str):
    """测试日记润色接口（非 Agent，直接 LLM 调用）。"""
    _divider()
    print("🧪 场景：日记润色 /polish")
    print(f"   📝 原文：{text[:80]}")

    try:
        resp = requests.post(
            f"{BASE_URL}/ai/polish",
            json={"content": text},
            timeout=TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        print("   ❌ 连接失败")
        return False

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code}: {resp.text[:200]}")
        return False

    polished = resp.json().get("polished", "")
    print(f"   ✨ 润色后：{polished[:120]}{'...' if len(polished) > 120 else ''}")
    print("   ✅ 润色成功")
    return True


def main():
    print("=" * 60)
    print("🤖 ReAct Agent 手动测试脚本")
    print(f"   目标服务：{BASE_URL}")
    print("=" * 60)

    results = []

    # 场景 1：闲聊（Agent 应直接回答，不调工具）
    results.append(
        test_scenario(
            name="纯闲聊",
            question="你好，给我讲一个关于旅游的冷笑话",
            expected_in_source="AI闲聊",
        )
    )

    # 场景 2：内部知识检索（Agent 应调用 search_internal_knowledge）
    results.append(
        test_scenario(
            name="内部知识检索（RAG）",
            question="根据同学们的日记，校园里有哪些值得去的地方？",
            expected_in_source="RAG",
        )
    )

    # 场景 3：实时信息（Agent 应调用 search_web_knowledge）
    results.append(
        test_scenario(
            name="实时信息（联网）",
            question="北京今天天气怎么样？适合出游吗？",
            expected_in_source="互联网搜索",
        )
    )

    # 场景 4：润色接口（直接 LLM，非 Agent 链路）
    results.append(
        test_polish("今天去爬山，风景很美，心情很好，值得推荐。")
    )

    _divider()
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n📊 测试结果：{passed}/{total} 通过")

    if passed < total:
        print("⚠️  部分场景未通过，请检查：")
        print("   1. 后端服务是否正在运行")
        print("   2. .env 中 AI 密钥是否正确配置")
        print("   3. TAVILY_API_KEY 是否配置（联网场景需要）")
        sys.exit(1)
    else:
        print("✅ 全部场景通过！")


if __name__ == "__main__":
    main()
