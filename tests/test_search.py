from fastapi.testclient import TestClient

from helpers import prepare_test_env, register_and_login


prepare_test_env("search", vector=True)

import api  # noqa: E402


def main():
    with TestClient(api.app) as client:
        headers = register_and_login(client, "search_user")
        create = client.post(
            "/diaries/",
            json={
                "scope": "campus",
                "spot_id": 44,
                "title": "学生食堂搜索测试",
                "content": "这里用于验证日记搜索。",
                "media_files": [],
            },
            headers=headers,
        )
        assert create.status_code == 200, create.text

        diary_search = client.get("/diaries/search", params={"keyword": "食堂"})
        assert diary_search.status_code == 200, diary_search.text
        assert any(item["title"] == "学生食堂搜索测试" for item in diary_search.json())

        spot_search = client.get("/spots/search", params={"query": "学一"})
        assert spot_search.status_code == 200, spot_search.text
        assert spot_search.json()
        assert spot_search.json()[0]["scope"] == "campus"

    print("✅ 日记搜索与景点搜索测试通过")


if __name__ == "__main__":
    main()
