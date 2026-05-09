from fastapi.testclient import TestClient

from helpers import prepare_test_env, register_and_login


prepare_test_env("rag", vector=True)

import ai  # noqa: E402
import api  # noqa: E402


class _FakeResponse:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeRagLLM:
    def __init__(self):
        self._router_called = False

    def invoke(self, messages):
        if not self._router_called:
            self._router_called = True
            return _FakeResponse("rag")
        return _FakeResponse("根据日记，学一食堂早餐种类多，适合作为推荐。")

    def bind_tools(self, tools):
        class _WithTools:
            def __init__(self):
                self._called = False

            def invoke(self, messages):
                if not self._called:
                    self._called = True
                    return _FakeResponse(
                        "",
                        tool_calls=[
                            {
                                "name": "search_internal_knowledge",
                                "args": {"query": "食堂 推荐"},
                                "id": "call_rag_test",
                            }
                        ],
                    )
                return _FakeResponse("根据日记，学一食堂早餐种类多，适合作为推荐。")

        return _WithTools()


def main():
    with TestClient(api.app) as client:
        headers = register_and_login(client, "rag_user")
        create = client.post(
            "/diaries/",
            json={
                "scope": "campus",
                "spot_id": 44,
                "title": "学一食堂早餐体验",
                "content": "早餐种类很多，价格也合适。",
                "media_files": [],
            },
            headers=headers,
        )
        assert create.status_code == 200, create.text

        ai.chat_llm = FakeRagLLM()
        rag_resp = client.post(
            "/ai/rag_chat",
            json={"message": "根据大家的日记，推荐一下食堂"},
        )
        assert rag_resp.status_code == 200, rag_resp.text
        data = rag_resp.json()
        assert "RAG" in data.get("source", "")
        assert "学一食堂" in data.get("reply", "")

        empty = client.post("/ai/rag_chat", json={"message": "   "})
        assert empty.status_code == 400, empty.text

    print("✅ RAG 路由、向量入库与空消息校验测试通过")


if __name__ == "__main__":
    main()
