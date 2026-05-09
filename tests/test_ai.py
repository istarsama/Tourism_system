from fastapi.testclient import TestClient

from helpers import prepare_test_env, register_and_login


prepare_test_env("ai", vector=True)

import ai  # noqa: E402
import api  # noqa: E402


class _FakeResponse:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    def __init__(self, route: str, answer: str):
        self.route = route
        self.answer = answer
        self._router_called = False

    def invoke(self, messages):
        if isinstance(messages, str):
            return _FakeResponse(f"润色后：{self.answer}")

        system_text = "\n".join(getattr(message, "content", "") for message in messages)
        if "对话标题" in system_text:
            return _FakeResponse("测试会话")

        if not self._router_called:
            self._router_called = True
            return _FakeResponse(self.route)

        return _FakeResponse(self.answer)

    def bind_tools(self, tools):
        route = self.route
        answer = self.answer

        class _WithTools:
            def __init__(self):
                self._called = False

            def invoke(self, messages):
                if not self._called:
                    self._called = True
                    tool_name = (
                        "search_web_knowledge"
                        if route == "web"
                        else "search_internal_knowledge"
                    )
                    return _FakeResponse(
                        "",
                        tool_calls=[
                            {
                                "name": tool_name,
                                "args": {"query": "测试查询"},
                                "id": f"call_{tool_name}",
                            }
                        ],
                    )
                return _FakeResponse(answer)

        return _WithTools()


def main():
    with TestClient(api.app) as client:
        ai.chat_llm = FakeLLM("chat", "你好，我是旅游系统助手。")
        chat = client.post("/ai/rag_chat", json={"message": "你好呀"})
        assert chat.status_code == 200, chat.text
        assert "闲聊" in chat.json()["source"]
        assert chat.json()["reply"]

        ai.chat_llm = FakeLLM("web", "明天适合轻装出行。")
        web = client.post("/ai/rag_chat", json={"message": "北京明天天气怎么样"})
        assert web.status_code == 200, web.text
        assert "Web" in web.json()["source"]
        assert "轻装" in web.json()["reply"]

        ai.chat_llm = FakeLLM("chat", "今天的校园游记更自然。")
        polish = client.post("/ai/polish", json={"content": "今天玩得不错"})
        assert polish.status_code == 200, polish.text
        assert "润色后" in polish.json()["polished"]

        headers = register_and_login(client, "ai_session_user")
        ai.chat_llm = FakeLLM("chat", "会话持久化回答。")
        session_resp = client.post(
            "/ai/rag_chat",
            json={"message": "帮我记一条旅游计划"},
            headers=headers,
        )
        assert session_resp.status_code == 200, session_resp.text
        session_id = session_resp.json()["session_id"]
        assert session_id

        sessions = client.get("/ai/sessions", headers=headers)
        assert sessions.status_code == 200, sessions.text
        assert any(item["id"] == session_id for item in sessions.json())

        messages = client.get(f"/ai/sessions/{session_id}/messages", headers=headers)
        assert messages.status_code == 200, messages.text
        roles = [item["role"] for item in messages.json()]
        assert roles == ["user", "assistant"]

    print("✅ AI 闲聊、联网路由、润色与会话持久化测试通过")


if __name__ == "__main__":
    main()
